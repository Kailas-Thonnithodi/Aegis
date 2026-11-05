import json
import sqlite3
from collections.abc import Callable
from functools import cache
from typing import Literal

from pydantic import BaseModel

from backend import db
from backend.db import DATA
from backend.models import Outcome, Step

EVALS = DATA / "evals"

ClaimSet = Literal["queue", "held_out"]
Score = Literal["match", "payout_miss", "outcome_miss", "not_finished"]


class CalculationStep(BaseModel):
    step: str
    amount: float


class HandlerDecision(BaseModel):
    claim_id: str
    set: ClaimSet
    decision: Outcome
    payout: float
    reason: str
    reference: str
    calculation: list[CalculationStep]
    tests: str
    difficulty: str
    needs: list[str]


class Scored(BaseModel):
    set: ClaimSet
    claim_type: str
    difficulty: str
    score: Score
    outcome_match: bool
    payout_match: bool


class Tally(BaseModel):
    claims: int
    matches: int
    outcome_matches: int
    payout_matches: int


class CheckSummary(BaseModel):
    overall: Tally
    without_manual: Tally
    by_set: dict[str, Tally]
    by_difficulty: dict[str, Tally]
    by_claim_type: dict[str, Tally]


def read(name: str) -> list[dict[str, object]]:
    return json.loads((EVALS / name).read_text())


@cache
def answer_key() -> dict[str, HandlerDecision]:
    sets: list[tuple[ClaimSet, str]] = [
        ("queue", "decisions.json"),
        ("held_out", "held_out_decisions.json"),
    ]
    return {
        decision.claim_id: decision
        for claim_set, name in sets
        for decision in (
            HandlerDecision.model_validate({**row, "set": claim_set})
            for row in read(name)
        )
    }


def held_out_claims() -> list[dict[str, object]]:
    return read("held_out_claims.json")


def score(
    outcome: Outcome | None, payout: float | None, handler: HandlerDecision
) -> tuple[Score, bool, bool]:
    """Score one decision: the score, whether the outcome and the payout match."""
    if outcome is None or payout is None:
        return "not_finished", False, False
    outcome_match = outcome == handler.decision
    payout_match = round(payout, 2) == round(handler.payout, 2)
    if not outcome_match:
        return "outcome_miss", False, payout_match
    if not payout_match:
        return "payout_miss", True, False
    return "match", True, True


def tally(results: list[Scored]) -> Tally:
    return Tally(
        claims=len(results),
        matches=sum(r.score == "match" for r in results),
        outcome_matches=sum(r.outcome_match for r in results),
        payout_matches=sum(r.payout_match for r in results),
    )


def grouped(results: list[Scored], key: Callable[[Scored], str]) -> dict[str, Tally]:
    groups = sorted({key(r) for r in results})
    return {g: tally([r for r in results if key(r) == g]) for g in groups}


def summarize(results: list[Scored]) -> CheckSummary:
    return CheckSummary(
        overall=tally(results),
        without_manual=tally([r for r in results if r.difficulty != "manual"]),
        by_set=grouped(results, lambda r: r.set),
        by_difficulty=grouped(results, lambda r: r.difficulty),
        by_claim_type=grouped(results, lambda r: r.claim_type),
    )


class CheckRequest(BaseModel):
    claim_ids: list[str]


class CheckRunSummary(BaseModel):
    run_id: int
    started_at: str
    finished_at: str | None
    claims: int
    done: int
    matches: int


class CheckClaim(BaseModel):
    claim_id: str
    set: ClaimSet
    claim_type: str
    summary: str
    amount_claimed: float
    difficulty: str
    handler_outcome: Outcome


class AgentDecision(BaseModel):
    outcome: Outcome | None
    payout: float | None
    reasons: str | None
    policy_section: str | None


class CheckResult(BaseModel):
    claim_id: str
    claim_type: str
    summary: str
    score: Score | None
    agent: AgentDecision
    handler: HandlerDecision
    steps: list[Step]


class CheckRun(CheckRunSummary):
    summary: CheckSummary
    results: list[CheckResult]


def check_claims() -> list[dict[str, object]]:
    return db.queue_claims() + held_out_claims()


@cache
def claims_by_id() -> dict[str, dict[str, object]]:
    return {str(claim["claim_id"]): claim for claim in check_claims()}


def list_claims() -> list[CheckClaim]:
    key = answer_key()
    return [
        CheckClaim.model_validate(
            {
                **claim,
                "set": key[claim_id].set,
                "difficulty": key[claim_id].difficulty,
                "handler_outcome": key[claim_id].decision,
            }
        )
        for claim_id, claim in claims_by_id().items()
    ]


def to_result(row: sqlite3.Row) -> CheckResult:
    claim = claims_by_id()[row["claim_id"]]
    return CheckResult.model_validate(
        {
            "claim_id": row["claim_id"],
            "claim_type": claim["claim_type"],
            "summary": claim["summary"],
            "score": row["score"],
            "agent": {
                "outcome": row["outcome"],
                "payout": row["payout"],
                "reasons": row["reasons"],
                "policy_section": row["policy_section"],
            },
            "handler": answer_key()[row["claim_id"]],
            "steps": json.loads(row["steps"] or "[]"),
        }
    )


def to_scored(result: CheckResult, row: sqlite3.Row) -> Scored:
    return Scored.model_validate(
        {
            "set": result.handler.set,
            "claim_type": result.claim_type,
            "difficulty": result.handler.difficulty,
            "score": row["score"],
            "outcome_match": bool(row["outcome_match"]),
            "payout_match": bool(row["payout_match"]),
        }
    )


def check_run(conn: sqlite3.Connection, run_id: int) -> CheckRun:
    rows = conn.execute(
        "select * from check_results where run_id = ? order by position",
        (run_id,),
    ).fetchall()
    results = [to_result(row) for row in rows]
    scored = [
        to_scored(r, row) for r, row in zip(results, rows, strict=True) if r.score
    ]
    return CheckRun(
        **run_summary(conn, run_id).model_dump(),
        summary=summarize(scored),
        results=results,
    )


def record_result(conn: sqlite3.Connection, run_id: int, claim_id: str) -> None:
    """Score the agent's work on a claim in checks.db and store the result."""
    check = db.connect(db.check_path())
    claim = check.execute(
        "select outcome, payout, reasons, policy_section from claims"
        " where claim_id = ?",
        (claim_id,),
    ).fetchone()
    steps = check.execute(
        "select at, title, detail from steps where claim_id = ? order by id",
        (claim_id,),
    ).fetchall()
    check.close()
    result, outcome_match, payout_match = score(
        claim["outcome"], claim["payout"], answer_key()[claim_id]
    )
    conn.execute(
        "update check_results set score = ?, outcome = ?, payout = ?, reasons = ?,"
        " policy_section = ?, steps = ?, outcome_match = ?, payout_match = ?"
        " where run_id = ? and claim_id = ?",
        (
            result,
            claim["outcome"],
            claim["payout"],
            claim["reasons"],
            claim["policy_section"],
            json.dumps([dict(step) for step in steps]),
            outcome_match,
            payout_match,
            run_id,
            claim_id,
        ),
    )
    conn.commit()


def finish(conn: sqlite3.Connection, run_id: int) -> None:
    conn.execute(
        "update check_results set score = 'not_finished', outcome_match = 0,"
        " payout_match = 0 where run_id = ? and score is null",
        (run_id,),
    )
    conn.execute(
        "update check_runs set finished_at = ? where id = ?", (db.now(), run_id)
    )
    conn.commit()


def run_summary(conn: sqlite3.Connection, run_id: int) -> CheckRunSummary:
    run = conn.execute("select * from check_runs where id = ?", (run_id,)).fetchone()
    counts = conn.execute(
        "select count(*) as claims, count(score) as done,"
        " coalesce(sum(score = 'match'), 0) as matches"
        " from check_results where run_id = ?",
        (run_id,),
    ).fetchone()
    return CheckRunSummary(
        run_id=run_id,
        started_at=run["started_at"],
        finished_at=run["finished_at"],
        claims=counts["claims"],
        done=counts["done"],
        matches=counts["matches"],
    )

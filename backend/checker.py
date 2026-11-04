import json
from collections.abc import Callable
from functools import cache
from typing import Literal

from pydantic import BaseModel

from backend.db import DATA
from backend.models import Outcome

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

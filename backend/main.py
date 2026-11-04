import json
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Decision,
    PaymentRequest,
    Policy,
    Step,
    StepRequest,
    Text,
)

SIGN_OFF_LIMIT = 1000.0
INSTRUCTIONS = Path(__file__).parent / "agent_instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    db.init()
    yield


app = FastAPI(title="Aegis", lifespan=lifespan)

Db = Annotated[sqlite3.Connection, Depends(db.get_db)]


def claim_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = conn.execute(
        "select * from claims where claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No claim {claim_id}")
    return row


def require_status(row: sqlite3.Row, status: str, message: str) -> None:
    if row["status"] != status:
        raise HTTPException(409, message)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def pay(conn: sqlite3.Connection, claim_id: str, amount: float) -> None:
    conn.execute("insert into payments values (?, ?, ?)", (claim_id, amount, now()))
    conn.execute("update claims set status = 'decided' where claim_id = ?", (claim_id,))
    conn.commit()


def decision_fields(row: sqlite3.Row) -> dict[str, object]:
    return {"status": row["status"], "outcome": row["outcome"], "payout": row["payout"]}


def to_claim(conn: sqlite3.Connection, row: sqlite3.Row) -> Claim:
    payment = conn.execute(
        "select amount, paid_at from payments where claim_id = ?", (row["claim_id"],)
    ).fetchone()
    return Claim.model_validate(
        {
            **json.loads(row["record"]),
            **decision_fields(row),
            "reasons": row["reasons"],
            "policy_section": row["policy_section"],
            "signed_off_at": row["signed_off_at"],
            "payment": dict(payment) if payment else None,
        }
    )


def to_summary(row: sqlite3.Row) -> ClaimSummary:
    return ClaimSummary.model_validate(
        {**json.loads(row["record"]), **decision_fields(row)}
    )


@app.get("/api/health", operation_id="get_health")
def get_health() -> dict[str, str]:
    """Report that the backend is up."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: Db) -> list[ClaimSummary]:
    """List the claims queue with where each claim stands."""
    rows = conn.execute("select * from claims order by claim_id").fetchall()
    return [to_summary(row) for row in rows]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: Db) -> Claim:
    """Get a claim in full, with its decision and payment."""
    return to_claim(conn, claim_row(conn, claim_id))


@app.get("/api/claims/{claim_id}/history", operation_id="get_claim_history")
def get_claim_history(claim_id: str, conn: Db) -> list[ClaimSummary]:
    """List the customer's other claims."""
    row = claim_row(conn, claim_id)
    rows = conn.execute(
        "select * from claims where customer_id = ? and claim_id != ?"
        " order by claim_id",
        (row["customer_id"], claim_id),
    ).fetchall()
    return [to_summary(other) for other in rows]


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: Db) -> Policy:
    """Get a customer's policy."""
    row = conn.execute(
        "select record from policies where policy_id = ?", (policy_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No policy {policy_id}")
    return Policy.model_validate_json(row["record"])


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording that claims are decided from."""
    return Text(text=(db.DATA / "policy_wording.md").read_text())


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, conn: Db) -> Claim:
    """Mark a waiting claim as in progress."""
    row = claim_row(conn, claim_id)
    require_status(row, "waiting", f"Claim {claim_id} is not waiting")
    conn.execute(
        "update claims set status = 'in_progress' where claim_id = ?", (claim_id,)
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision, conn: Db) -> Claim:
    """Record the decision on a claim in progress."""
    row = claim_row(conn, claim_id)
    require_status(row, "in_progress", f"Claim {claim_id} is not in progress")
    if row["outcome"] is not None:
        raise HTTPException(409, f"Claim {claim_id} already has a decision")
    approved = decision.outcome == "approve"
    if approved and decision.payout <= 0:
        raise HTTPException(422, "An approval needs a payout above $0.00")
    if not approved and decision.payout != 0:
        raise HTTPException(422, "Only an approval has a payout")
    if not approved:
        status = "decided"
    elif decision.payout > SIGN_OFF_LIMIT:
        status = "waiting_for_signoff"
    else:
        status = "in_progress"
    conn.execute(
        "update claims set status = ?, outcome = ?, payout = ?, reasons = ?,"
        " policy_section = ? where claim_id = ?",
        (
            status,
            decision.outcome,
            round(decision.payout, 2),
            decision.reasons,
            decision.policy_section,
            claim_id,
        ),
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentRequest, conn: Db) -> Claim:
    """Pay the approved payout on a claim."""
    claim = get_claim(claim_id, conn)
    if claim.outcome != "approve" or claim.payout is None:
        raise HTTPException(409, f"Claim {claim_id} is not approved")
    if claim.payment is not None:
        raise HTTPException(409, f"Claim {claim_id} is already paid")
    if claim.payout > SIGN_OFF_LIMIT:
        raise HTTPException(409, "This payout needs a handler's sign-off")
    if payment.amount != claim.payout:
        raise HTTPException(
            409, f"The amount must match the approved payout of {money(claim.payout)}"
        )
    pay(conn, claim_id, claim.payout)
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, conn: Db) -> Claim:
    """Sign off a payout over $1,000 and release the payment."""
    row = claim_row(conn, claim_id)
    require_status(
        row, "waiting_for_signoff", f"Claim {claim_id} is not waiting for sign-off"
    )
    conn.execute(
        "update claims set signed_off_at = ? where claim_id = ?", (now(), claim_id)
    )
    pay(conn, claim_id, row["payout"])
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/reset", operation_id="reset_claim")
def reset_claim(claim_id: str, conn: Db) -> Claim:
    """Return an unfinished claim to the queue, clearing its decision."""
    row = claim_row(conn, claim_id)
    require_status(row, "in_progress", f"Claim {claim_id} is not in progress")
    conn.execute(
        "update claims set status = 'waiting', outcome = null, payout = null,"
        " reasons = null, policy_section = null where claim_id = ?",
        (claim_id,),
    )
    conn.commit()
    return get_claim(claim_id, conn)


@app.post("/api/claims/{claim_id}/steps", operation_id="record_step")
def record_step(claim_id: str, step: StepRequest, conn: Db) -> Step:
    """Record a step the agent took on a claim."""
    claim_row(conn, claim_id)
    recorded = Step(at=now(), title=step.title, detail=step.detail)
    conn.execute(
        "insert into steps (claim_id, at, title, detail) values (?, ?, ?, ?)",
        (claim_id, recorded.at, recorded.title, recorded.detail),
    )
    conn.commit()
    return recorded


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, conn: Db) -> list[Step]:
    """List the steps the agent took on a claim, in order."""
    claim_row(conn, claim_id)
    rows = conn.execute(
        "select at, title, detail from steps where claim_id = ? order by id",
        (claim_id,),
    ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@app.get("/api/instructions", operation_id="get_agent_instructions")
def get_agent_instructions() -> Text:
    """Get the Aegis Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text())

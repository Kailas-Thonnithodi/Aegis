import json
import sqlite3
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import Claim, ClaimSummary, Policy, Text


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

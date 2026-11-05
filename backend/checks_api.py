from fastapi import APIRouter, HTTPException

from backend import checker, db, runner
from backend.checker import CheckClaim, CheckRequest, CheckRun, CheckRunSummary

router = APIRouter()


@router.get("/api/checks/claims", operation_id="list_check_claims")
def list_check_claims() -> list[CheckClaim]:
    """List every claim that can be checked, from both sets, for the picker."""
    return checker.list_claims()


@router.get("/api/checks", operation_id="list_check_runs")
def list_check_runs(conn: db.Db) -> list[CheckRunSummary]:
    """List every check run, newest first, with its progress and matches."""
    rows = conn.execute("select id from check_runs order by id desc").fetchall()
    return [checker.run_summary(conn, row["id"]) for row in rows]


@router.get("/api/checks/{run_id}", operation_id="get_check_run")
def get_check_run(run_id: int, conn: db.Db) -> CheckRun:
    """Get a check run: its scores and each claim's result beside the handler's."""
    if (
        conn.execute("select 1 from check_runs where id = ?", (run_id,)).fetchone()
        is None
    ):
        raise HTTPException(404, f"No check run {run_id}")
    return checker.check_run(conn, run_id)


@router.post("/api/checks", operation_id="start_check", status_code=202)
def start_check(request: CheckRequest, conn: db.Db) -> CheckRunSummary:
    """Start a check run: the agent works the picked claims and is scored."""
    claim_ids = list(dict.fromkeys(request.claim_ids))
    if not claim_ids:
        raise HTTPException(422, "Pick at least one claim to check")
    key = checker.answer_key()
    unknown = [claim_id for claim_id in claim_ids if claim_id not in key]
    if unknown:
        raise HTTPException(404, f"No claim {unknown[0]}")
    run_id: int = conn.execute(
        "insert into check_runs (started_at) values (?) returning id", (db.now(),)
    ).fetchone()["id"]
    conn.executemany(
        "insert into check_results (run_id, position, claim_id) values (?, ?, ?)",
        [(run_id, index, claim_id) for index, claim_id in enumerate(claim_ids)],
    )
    conn.commit()
    runner.enqueue_check(run_id)
    return checker.run_summary(conn, run_id)

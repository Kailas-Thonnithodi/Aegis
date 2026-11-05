from fastapi import APIRouter, HTTPException

from backend import checker, db, runner
from backend.checker import CheckRequest, CheckRunSummary

router = APIRouter()


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

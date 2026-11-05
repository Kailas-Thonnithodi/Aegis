import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from agent import main as agent
from backend import checker, db

worker = ThreadPoolExecutor(max_workers=1)
queued: list[str] = []
lock = threading.Lock()


def is_waiting(claim_id: str) -> bool:
    conn = db.connect(db.main_path())
    row = conn.execute(
        "select status from claims where claim_id = ?", (claim_id,)
    ).fetchone()
    conn.close()
    return row["status"] == "waiting"


def work(claim_id: str) -> None:
    try:
        if is_waiting(claim_id):
            agent.run(claim_id, str(uuid.uuid4()))
    finally:
        with lock:
            queued.remove(claim_id)


def enqueue(claim_ids: list[str]) -> list[str]:
    with lock:
        added = [claim_id for claim_id in claim_ids if claim_id not in queued]
        queued.extend(added)
    for claim_id in added:
        worker.submit(work, claim_id)
    return added


def work_check(run_id: int) -> None:
    conn = db.connect(db.main_path())
    rows = conn.execute(
        "select claim_id from check_results where run_id = ? order by position",
        (run_id,),
    ).fetchall()
    try:
        db.rebuild(db.check_path(), checker.check_claims())
        for row in rows:
            agent.run(
                row["claim_id"],
                str(uuid.uuid4()),
                base_url=f"{agent.BACKEND_URL}/check",
            )
            checker.record_result(conn, run_id, row["claim_id"])
    finally:
        checker.finish(conn, run_id)
        conn.close()


def enqueue_check(run_id: int) -> None:
    worker.submit(work_check, run_id)

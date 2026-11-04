import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from agent import main as agent
from backend import db

worker = ThreadPoolExecutor(max_workers=1)
queued: list[str] = []
lock = threading.Lock()


def is_waiting(claim_id: str) -> bool:
    conn = db.connect()
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

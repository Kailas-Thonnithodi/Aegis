import json
import os
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends

DATA = Path(__file__).parent.parent / "data"

SCHEMA = """
create table if not exists policies (
    policy_id text primary key,
    record text not null
);
create table if not exists claims (
    claim_id text primary key,
    customer_id text not null,
    record text not null,
    status text not null,
    outcome text,
    payout real,
    reasons text,
    policy_section text,
    signed_off_at text
);
create table if not exists payments (
    claim_id text primary key,
    amount real not null,
    paid_at text not null
);
create table if not exists steps (
    id integer primary key,
    claim_id text not null,
    at text not null,
    title text not null,
    detail text not null
);
create table if not exists check_runs (
    id integer primary key,
    started_at text not null,
    finished_at text
);
create table if not exists check_results (
    run_id integer not null,
    position integer not null,
    claim_id text not null,
    score text,
    outcome text,
    payout real,
    reasons text,
    policy_section text,
    steps text,
    outcome_match integer,
    payout_match integer,
    primary key (run_id, claim_id)
);
"""

TABLES = ["policies", "claims", "payments", "steps", "check_runs", "check_results"]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def main_path() -> str:
    return os.environ.get("AEGIS_DB", "aegis.db")


def check_path() -> str:
    return os.environ.get("AEGIS_CHECK_DB", "checks.db")


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.row_factory = sqlite3.Row
    return db


def get_db() -> Iterator[sqlite3.Connection]:
    db = connect(main_path())
    try:
        yield db
    finally:
        db.close()


Db = Annotated[sqlite3.Connection, Depends(get_db)]


def get_check_db() -> Iterator[sqlite3.Connection]:
    db = connect(check_path())
    try:
        yield db
    finally:
        db.close()


def queue_claims() -> list[dict[str, object]]:
    return json.loads((DATA / "claims.json").read_text())


def seed(db: sqlite3.Connection, claims: list[dict[str, object]]) -> tuple[int, int]:
    policies = json.loads((DATA / "policies.json").read_text())
    db.executemany(
        "insert into policies values (?, ?)",
        [(p["policy_id"], json.dumps(p)) for p in policies],
    )
    records = [{k: v for k, v in c.items() if k != "status"} for c in claims]
    db.executemany(
        "insert into claims (claim_id, customer_id, record, status)"
        " values (?, ?, ?, 'waiting')",
        [(c["claim_id"], c["customer_id"], json.dumps(c)) for c in records],
    )
    db.commit()
    return len(claims), len(policies)


def init() -> None:
    db = connect(main_path())
    db.executescript(SCHEMA)
    if db.execute("select count(*) from claims").fetchone()[0] == 0:
        seed(db, queue_claims())
    db.close()


def rebuild(path: str, claims: list[dict[str, object]]) -> tuple[int, int]:
    db = connect(path)
    db.executescript(
        "".join(f"drop table if exists {table};" for table in TABLES) + SCHEMA
    )
    counts = seed(db, claims)
    db.close()
    return counts


def reset() -> tuple[int, int]:
    return rebuild(main_path(), queue_claims())

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

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
"""


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(
        os.environ.get("AEGIS_DB", "aegis.db"), check_same_thread=False
    )
    db.row_factory = sqlite3.Row
    return db


def get_db() -> Iterator[sqlite3.Connection]:
    db = connect()
    try:
        yield db
    finally:
        db.close()


def seed(db: sqlite3.Connection) -> tuple[int, int]:
    policies = json.loads((DATA / "policies.json").read_text())
    claims = json.loads((DATA / "claims.json").read_text())
    db.executemany(
        "insert into policies values (?, ?)",
        [(p["policy_id"], json.dumps(p)) for p in policies],
    )
    for claim in claims:
        del claim["status"]
    db.executemany(
        "insert into claims (claim_id, customer_id, record, status)"
        " values (?, ?, ?, 'waiting')",
        [(c["claim_id"], c["customer_id"], json.dumps(c)) for c in claims],
    )
    db.commit()
    return len(claims), len(policies)


def init() -> None:
    db = connect()
    db.executescript(SCHEMA)
    if db.execute("select count(*) from claims").fetchone()[0] == 0:
        seed(db)
    db.close()


def reset() -> tuple[int, int]:
    db = connect()
    db.executescript(
        "drop table if exists policies; drop table if exists claims;"
        "drop table if exists payments; drop table if exists steps;" + SCHEMA
    )
    counts = seed(db)
    db.close()
    return counts

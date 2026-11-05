import json
import sqlite3
from contextlib import closing

import pytest

from agent import main as agent
from backend import checker, db, runner


class FakeWorker:
    def __init__(self):
        self.jobs = []

    def submit(self, fn, *args):
        self.jobs.append((fn, args))

    def run_all(self):
        while self.jobs:
            fn, args = self.jobs.pop(0)
            fn(*args)


@pytest.fixture
def worker(client, agent_backend, monkeypatch):
    fake = FakeWorker()
    monkeypatch.setattr(runner, "worker", fake)
    return fake


def results(tmp_path, run_id):
    with closing(sqlite3.connect(tmp_path / "test.db")) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "select * from check_results where run_id = ? order by position",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def start(client, claim_ids):
    return client.post("/api/checks", json={"claim_ids": claim_ids})


def test_a_check_run_scores_each_claim_and_keeps_its_steps(client, worker, tmp_path):
    response = start(client, ["CLM-1001", "CLM-1101", "CLM-1001"])

    assert response.status_code == 202
    run = response.json()
    assert run["claims"] == 2
    assert run["done"] == 0
    assert run["finished_at"] is None

    worker.run_all()

    first, second = results(tmp_path, run["run_id"])
    assert first["claim_id"] == "CLM-1001"
    assert first["score"] == "match"
    assert first["payout"] == 420
    assert [s["title"] for s in json.loads(first["steps"])][:2] == [
        "Read the claim",
        "Decided: approve, $420.00",
    ]
    assert second["claim_id"] == "CLM-1101"
    assert second["score"] == "payout_miss"
    assert second["outcome_match"] == 1
    assert second["payout_match"] == 0


def test_a_check_run_leaves_the_live_queue_untouched(client, worker):
    client.post("/api/claims/CLM-1001/start")
    before = client.get("/api/claims").json()

    start(client, ["CLM-1001", "CLM-1002"])
    worker.run_all()

    assert client.get("/api/claims").json() == before
    assert client.get("/api/claims/CLM-1002/steps").json() == []


def test_start_check_needs_at_least_one_claim(client, worker):
    response = start(client, [])

    assert response.status_code == 422
    assert response.json()["detail"] == "Pick at least one claim to check"


def test_start_check_refuses_an_unknown_claim(client, worker):
    response = start(client, ["CLM-1001", "CLM-9999"])

    assert response.status_code == 404
    assert response.json()["detail"] == "No claim CLM-9999"


def test_a_run_that_fails_marks_its_claims_not_finished(
    client, worker, tmp_path, monkeypatch
):
    def fail(claim_id, thread_id, base_url):
        raise RuntimeError("backend unreachable")

    monkeypatch.setattr(agent, "run", fail)
    run = start(client, ["CLM-1001"]).json()

    with pytest.raises(RuntimeError):
        worker.run_all()
    assert results(tmp_path, run["run_id"])[0]["score"] == "not_finished"
    assert client.get("/api/claims").json()[0]["status"] == "waiting"


def test_the_check_api_serves_claims_and_no_handler_decisions(client):
    db.rebuild(db.check_path(), checker.check_claims())
    handler = checker.answer_key()["CLM-1101"]

    claims = client.get("/check/api/claims").json()
    claim = client.get("/check/api/claims/CLM-1101")

    assert len(claims) == 50
    assert {c["status"] for c in claims} == {"waiting"}
    assert "difficulty" not in claim.json()
    assert "calculation" not in claim.json()
    assert handler.reason not in claim.text
    assert client.get("/check/api/claims/CLM-1101/history").json() == []
    assert len(client.get("/api/claims").json()) == 25


def test_list_check_claims_covers_both_sets(client):
    claims = client.get("/api/checks/claims").json()

    assert len(claims) == 50
    for claim_set in ("queue", "held_out"):
        in_set = [c for c in claims if c["set"] == claim_set]
        assert len(in_set) == 25
        assert sum(c["difficulty"] == "manual" for c in in_set) == 5
    assert claims[0]["claim_id"] == "CLM-1001"
    assert claims[0]["handler_outcome"] == "approve"


def test_get_check_run_shows_scores_and_both_decisions(client, worker):
    run_id = start(client, ["CLM-1001", "CLM-1101"]).json()["run_id"]
    worker.run_all()

    run = client.get(f"/api/checks/{run_id}").json()

    assert run["done"] == 2
    assert run["matches"] == 1
    assert run["finished_at"] is not None
    assert run["summary"]["overall"] == {
        "claims": 2,
        "matches": 1,
        "outcome_matches": 2,
        "payout_matches": 1,
    }
    assert set(run["summary"]["by_set"]) == {"queue", "held_out"}
    match, miss = run["results"]
    assert match["claim_id"] == "CLM-1001"
    assert match["score"] == "match"
    assert match["handler"]["payout"] == 420
    assert match["steps"][0]["title"] == "Read the claim"
    assert miss["score"] == "payout_miss"
    assert miss["agent"]["payout"] == 2580
    assert miss["handler"]["payout"] == 580
    assert miss["handler"]["calculation"]


def test_a_check_run_in_progress_counts_only_finished_claims(client, worker):
    run_id = start(client, ["CLM-1001"]).json()["run_id"]

    run = client.get(f"/api/checks/{run_id}").json()

    assert run["done"] == 0
    assert run["results"][0]["score"] is None
    assert run["results"][0]["steps"] == []
    assert run["summary"]["overall"]["claims"] == 0


def test_list_check_runs_is_newest_first(client, worker):
    first = start(client, ["CLM-1001"]).json()["run_id"]
    second = start(client, ["CLM-1101"]).json()["run_id"]
    worker.run_all()

    runs = client.get("/api/checks").json()

    assert [r["run_id"] for r in runs] == [second, first]
    assert runs[1]["matches"] == 1


def test_unknown_check_run_is_not_found(client):
    response = client.get("/api/checks/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "No check run 99"

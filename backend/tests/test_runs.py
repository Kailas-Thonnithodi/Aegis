import pytest

from agent import main as agent
from backend import runner


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
    monkeypatch.setattr(runner, "queued", [])
    return fake


def test_run_agent_queues_a_claim_and_works_it(client, worker):
    response = client.post("/api/claims/CLM-1001/run")

    assert response.status_code == 202
    assert response.json() == {"running": True, "claims_left": 1}

    worker.run_all()

    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    assert client.get("/api/queue").json() == {"running": False, "claims_left": 0}


def test_run_agent_needs_a_waiting_claim(client, worker):
    client.post("/api/claims/CLM-1001/start")
    response = client.post("/api/claims/CLM-1001/run")

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not waiting"


def test_run_agent_refuses_a_claim_already_queued(client, worker):
    client.post("/api/claims/CLM-1001/run")
    response = client.post("/api/claims/CLM-1001/run")

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is already queued"


def test_work_queue_works_every_waiting_claim(client, worker):
    client.post("/api/claims/CLM-1001/start")
    response = client.post("/api/queue/run")

    assert response.status_code == 202
    assert response.json() == {"queued": 24}
    assert client.get("/api/queue").json() == {"running": True, "claims_left": 24}

    worker.run_all()

    claims = client.get("/api/claims").json()
    assert {c["status"] for c in claims[1:]} <= {"decided", "waiting_for_signoff"}
    for claim in claims[1:]:
        full = client.get(f"/api/claims/{claim['claim_id']}").json()
        assert (full["payment"] is None) == (full["payout"] > 1000)


def test_a_claim_no_longer_waiting_is_skipped(client, worker):
    client.post("/api/claims/CLM-1001/run")
    client.post("/api/claims/CLM-1001/start")

    worker.run_all()

    assert client.get("/api/claims/CLM-1001").json()["status"] == "in_progress"
    assert client.get("/api/claims/CLM-1001/steps").json() == []
    assert runner.queued == []


def test_a_failed_run_leaves_the_queue(client, worker, monkeypatch):
    def fail(claim_id, thread_id):
        raise RuntimeError("backend unreachable")

    monkeypatch.setattr(agent, "run", fail)
    client.post("/api/claims/CLM-1001/run")

    with pytest.raises(RuntimeError):
        worker.run_all()
    assert runner.queued == []

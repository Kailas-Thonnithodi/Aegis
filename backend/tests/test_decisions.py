import sqlite3
from contextlib import closing

import pytest

SIGN_OFF = "This payout needs a handler's sign-off"


def decide(client, claim_id, outcome, payout):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "outcome": outcome,
            "payout": payout,
            "reasons": "The reasons.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def started(client, claim_id):
    assert client.post(f"/api/claims/{claim_id}/start").status_code == 200


def payment_rows(tmp_path):
    with closing(sqlite3.connect(tmp_path / "test.db")) as conn:
        return conn.execute("select * from payments").fetchall()


def test_start_moves_a_waiting_claim_to_in_progress(client):
    claim = client.post("/api/claims/CLM-1001/start").json()

    assert claim["status"] == "in_progress"


def test_start_refuses_a_claim_that_is_not_waiting(client):
    started(client, "CLM-1001")
    response = client.post("/api/claims/CLM-1001/start")

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not waiting"


def test_start_of_unknown_claim_is_not_found(client):
    assert client.post("/api/claims/CLM-9999/start").status_code == 404


@pytest.mark.parametrize("outcome", ["decline", "refer"])
def test_decline_and_refer_decide_the_claim(client, outcome):
    started(client, "CLM-1001")
    claim = decide(client, "CLM-1001", outcome, 0).json()

    assert claim["status"] == "decided"
    assert claim["outcome"] == outcome
    assert claim["payout"] == 0
    assert claim["reasons"] == "The reasons."
    assert claim["policy_section"] == "Section 3, Trip Delay"


def test_approval_up_to_the_limit_waits_for_payment(client):
    started(client, "CLM-1001")
    claim = decide(client, "CLM-1001", "approve", 1000).json()

    assert claim["status"] == "in_progress"
    assert claim["payout"] == 1000


def test_approval_over_the_limit_waits_for_signoff(client):
    started(client, "CLM-1002")
    claim = decide(client, "CLM-1002", "approve", 1150).json()

    assert claim["status"] == "waiting_for_signoff"


def test_decision_needs_the_claim_in_progress(client):
    response = decide(client, "CLM-1001", "refer", 0)

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not in progress"


def test_decision_is_recorded_once(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "approve", 420)
    response = decide(client, "CLM-1001", "decline", 0)

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 already has a decision"


def test_approval_needs_a_payout(client):
    started(client, "CLM-1001")
    response = decide(client, "CLM-1001", "approve", 0)

    assert response.status_code == 422
    assert response.json()["detail"] == "An approval needs a payout above $0.00"


def test_only_an_approval_has_a_payout(client):
    started(client, "CLM-1001")
    response = decide(client, "CLM-1001", "decline", 50)

    assert response.status_code == 422
    assert response.json()["detail"] == "Only an approval has a payout"


def test_pay_claim_pays_an_approval_and_decides_it(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "approve", 420)
    claim = client.post("/api/claims/CLM-1001/payment", json={"amount": 420}).json()

    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420


def test_pay_claim_refuses_a_claim_that_is_not_approved(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "decline", 0)
    response = client.post("/api/claims/CLM-1001/payment", json={"amount": 420})

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not approved"


def test_pay_claim_refuses_a_payout_over_the_limit(client, tmp_path):
    started(client, "CLM-1002")
    decide(client, "CLM-1002", "approve", 1150)
    response = client.post("/api/claims/CLM-1002/payment", json={"amount": 1150})

    assert response.status_code == 409
    assert response.json()["detail"] == SIGN_OFF
    assert payment_rows(tmp_path) == []
    assert client.get("/api/claims/CLM-1002").json()["status"] == "waiting_for_signoff"


def test_pay_claim_refuses_the_wrong_amount(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "approve", 420)
    response = client.post("/api/claims/CLM-1001/payment", json={"amount": 500})

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The amount must match the approved payout of $420.00"
    )


def test_pay_claim_refuses_to_pay_twice(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "approve", 420)
    client.post("/api/claims/CLM-1001/payment", json={"amount": 420})
    response = client.post("/api/claims/CLM-1001/payment", json={"amount": 420})

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is already paid"


def test_sign_off_releases_the_payment(client, tmp_path):
    started(client, "CLM-1002")
    decide(client, "CLM-1002", "approve", 1150)
    claim = client.post("/api/claims/CLM-1002/sign-off").json()

    assert claim["status"] == "decided"
    assert claim["signed_off_at"] is not None
    assert claim["payment"]["amount"] == 1150
    assert [(row[0], row[1]) for row in payment_rows(tmp_path)] == [("CLM-1002", 1150)]


def test_sign_off_needs_a_claim_waiting_for_it(client):
    response = client.post("/api/claims/CLM-1001/sign-off")

    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not waiting for sign-off"


def test_reset_returns_an_unfinished_claim_to_the_queue(client):
    started(client, "CLM-1001")
    decide(client, "CLM-1001", "approve", 420)
    claim = client.post("/api/claims/CLM-1001/reset").json()

    assert claim["status"] == "waiting"
    assert claim["outcome"] is None
    assert claim["payout"] is None
    assert claim["reasons"] is None


def test_reset_needs_a_claim_in_progress(client):
    assert client.post("/api/claims/CLM-1001/reset").status_code == 409


def test_steps_are_recorded_and_listed_in_order(client):
    for title in ["Read the claim", "Read the policy wording"]:
        step = client.post(
            "/api/claims/CLM-1001/steps", json={"title": title, "detail": "Done."}
        ).json()
        assert step["title"] == title
        assert step["at"]

    steps = client.get("/api/claims/CLM-1001/steps").json()

    assert [step["title"] for step in steps] == [
        "Read the claim",
        "Read the policy wording",
    ]
    assert client.get("/api/claims/CLM-1002/steps").json() == []


def test_steps_of_unknown_claim_are_not_found(client):
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_instructions_are_served(client):
    text = client.get("/api/instructions").json()["text"]

    assert text.startswith("# Aegis Agent instructions")

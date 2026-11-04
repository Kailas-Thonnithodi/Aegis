from backend import db, seed


def test_list_claims_returns_the_queue_all_waiting(client):
    claims = client.get("/api/claims").json()

    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0]["claim_id"] == "CLM-1001"
    assert claims[0]["outcome"] is None


def test_get_claim_returns_it_in_full(client):
    claim = client.get("/api/claims/CLM-1001").json()

    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["policy_id"] == "POL-2001"
    assert claim["payout"] is None
    assert claim["payment"] is None


def test_unknown_claim_is_not_found(client):
    response = client.get("/api/claims/CLM-9999")

    assert response.status_code == 404
    assert response.json() == {"detail": "No claim CLM-9999"}


def test_claim_history_lists_the_customers_other_claims(client):
    history = client.get("/api/claims/CLM-1005/history").json()

    assert [claim["claim_id"] for claim in history] == ["CLM-1006"]
    assert client.get("/api/claims/CLM-1001/history").json() == []


def test_claim_history_of_unknown_claim_is_not_found(client):
    assert client.get("/api/claims/CLM-9999/history").status_code == 404


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()

    assert policy["plan"] == "premium"
    assert policy["travelers"] == ["Maya Patel"]


def test_unknown_policy_is_not_found(client):
    assert client.get("/api/policies/POL-9999").status_code == 404


def test_policy_wording_is_the_full_wording(client):
    text = client.get("/api/policy-wording").json()["text"]

    assert text.startswith("# Aegis Travel Insurance: Policy Wording")
    assert "## 10. How we work out your payment" in text


def test_init_keeps_existing_records(client):
    client.post("/api/claims/CLM-1001/start")
    db.init()

    assert len(client.get("/api/claims").json()) == 25


def test_reset_reloads_the_records(client):
    assert db.reset() == (25, 50)
    assert len(client.get("/api/claims").json()) == 25


def test_seed_reports_what_it_loaded(capsys):
    seed.main()

    assert capsys.readouterr().out == "Loaded 25 claims and 50 policies.\n"

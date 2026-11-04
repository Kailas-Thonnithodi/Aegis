from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from agent import __main__ as cli
from agent import main


class FakeModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def calls(*tool_calls):
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": f"call-{index}"}
            for index, (name, args) in enumerate(tool_calls)
        ],
    )


def fake(*messages):
    return FakeModel(messages=iter(messages))


def decision(outcome, payout):
    return {
        "claim_id": "CLM-1002",
        "outcome": outcome,
        "payout": payout,
        "reasons": "The suitcase was lost by the carrier.",
        "policy_section": "Section 5, Baggage and Personal Effects",
    }


def titles(backend, claim_id):
    return [
        step["title"] for step in backend.get(f"/api/claims/{claim_id}/steps").json()
    ]


def test_agent_reads_everything_and_records_each_step(backend):
    model = fake(
        calls(
            ("get_claim", {"claim_id": "CLM-1002"}),
            ("get_policy", {"policy_id": "POL-2002"}),
            ("get_claim_history", {"claim_id": "CLM-1002"}),
            ("get_policy_wording", {}),
        ),
        calls(("record_decision", decision("refer", 0))),
        AIMessage(content="Referred for the carrier's report."),
    )

    assert main.run("CLM-1002", "thread-1", model) == "decided"
    steps = titles(backend, "CLM-1002")
    assert set(steps[:4]) == {
        "Read the claim",
        "Read policy POL-2002",
        "Read the customer's claim history",
        "Read the policy wording",
    }
    assert steps[4:] == ["Decided: refer", "Note"]
    assert backend.get("/api/claims/CLM-1002").json()["outcome"] == "refer"


def test_payment_over_the_limit_is_held_for_signoff(backend):
    model = fake(
        calls(("record_decision", decision("approve", 1150))),
        calls(("pay_claim", {"claim_id": "CLM-1002", "amount": 1150})),
        AIMessage(content="Approved, waiting for sign-off."),
    )

    assert main.run("CLM-1002", "thread-2", model) == "waiting_for_signoff"
    claim = backend.get("/api/claims/CLM-1002").json()
    assert claim["payment"] is None
    assert titles(backend, "CLM-1002")[:2] == [
        "Decided: approve, $1,150.00",
        "Payment held for sign-off",
    ]


def test_approval_up_to_the_limit_is_paid(backend):
    model = fake(
        calls(
            ("record_decision", {**decision("approve", 420), "claim_id": "CLM-1001"})
        ),
        calls(("pay_claim", {"claim_id": "CLM-1001", "amount": 420})),
        AIMessage(content="Paid."),
    )

    assert main.run("CLM-1001", "thread-3", model) == "decided"
    assert titles(backend, "CLM-1001")[:2] == [
        "Decided: approve, $420.00",
        "Paid $420.00",
    ]


def test_refusals_are_recorded_as_steps(backend):
    model = fake(
        calls(("pay_claim", {"claim_id": "CLM-1002", "amount": 50})),
        calls(("record_decision", decision("decline", 50))),
        calls(("record_decision", decision("decline", 0))),
        AIMessage(content="Declined."),
    )

    assert main.run("CLM-1002", "thread-4", model) == "decided"
    assert titles(backend, "CLM-1002")[:3] == [
        "Payment refused",
        "Decision refused",
        "Decided: decline",
    ]


def test_unknown_tool_calls_get_a_plain_title():
    title = main.step_title({"name": "other", "args": {}, "id": "1"}, "{}")

    assert title == "Called other"


def test_a_run_that_stops_early_returns_the_claim_to_the_queue(backend):
    model = fake(AIMessage(content="I am not sure."))

    assert main.run("CLM-1001", "thread-5", model) == "waiting"
    steps = backend.get("/api/claims/CLM-1001/steps").json()
    assert steps[-1] == {
        "at": steps[-1]["at"],
        "title": "Returned to the queue",
        "detail": "The agent finished without completing the claim.",
    }
    assert backend.get("/api/claims/CLM-1001").json()["status"] == "waiting"


def test_a_run_that_fails_returns_the_claim_to_the_queue(backend):
    model = fake(
        calls(("record_decision", {**decision("approve", 420), "claim_id": "CLM-1001"}))
    )

    assert main.run("CLM-1001", "thread-6", model) == "waiting"
    detail = backend.get("/api/claims/CLM-1001/steps").json()[-1]["detail"]
    assert detail.startswith("The agent stopped with an error")
    assert backend.get("/api/claims/CLM-1001").json()["outcome"] is None


def test_stub_model_approves_and_pays(backend, monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "stub")

    assert main.run("CLM-1001", "thread-7") == "decided"
    claim = backend.get("/api/claims/CLM-1001").json()
    assert claim["payment"]["amount"] == 420
    assert titles(backend, "CLM-1001") == [
        "Read the claim",
        "Decided: approve, $420.00",
        "Paid $420.00",
        "Note",
    ]


def test_stub_model_is_held_for_signoff_over_the_limit(backend, monkeypatch):
    monkeypatch.setenv("MODEL_NAME", "stub")

    assert main.run("CLM-1002", "thread-8") == "waiting_for_signoff"


def test_default_model_uses_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")

    model = main.default_model()

    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "openrouter/free"
    assert model.rate_limiter is main.rate_limiter


def test_cli_prints_where_each_claim_stands(monkeypatch, capsys):
    monkeypatch.setattr(main, "run", lambda claim_id, thread_id: "decided")
    cli.cli(["CLM-1001"])

    assert capsys.readouterr().out == "CLM-1001: decided\n"

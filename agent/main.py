import json
import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolCall, ToolMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from agent.stub_model import StubModel

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
SIGN_OFF = "This payout needs a handler's sign-off"

checkpointer = InMemorySaver()
# OpenRouter allows new accounts 20 requests a minute per model; stay under it.
rate_limiter = InMemoryRateLimiter(requests_per_second=0.3)


def connect(base_url: str) -> httpx.Client:
    return httpx.Client(base_url=base_url, timeout=60)


def make_tools(client: httpx.Client) -> list[BaseTool]:
    def call(method: str, path: str, body: dict[str, object] | None = None) -> str:
        response = client.request(method, path, json=body)
        return response.text if response.is_success else f"Refused: {response.text}"

    @tool
    def get_claim(claim_id: str) -> str:
        """Get a claim in full: the story, the items claimed and the documents."""
        return call("GET", f"/api/claims/{claim_id}")

    @tool
    def get_policy(policy_id: str) -> str:
        """Get a customer's policy: plan, add-ons, trip dates, trip cost, travelers."""
        return call("GET", f"/api/policies/{policy_id}")

    @tool
    def get_claim_history(claim_id: str) -> str:
        """List the customer's other claims."""
        return call("GET", f"/api/claims/{claim_id}/history")

    @tool
    def get_policy_wording() -> str:
        """Get the policy wording that claims are decided from."""
        return json.loads(call("GET", "/api/policy-wording"))["text"]

    @tool
    def record_decision(
        claim_id: str,
        outcome: Literal["approve", "decline", "refer"],
        payout: float,
        reasons: str,
        policy_section: str,
    ) -> str:
        """Record the decision on a claim. The payout is 0 unless it is approved."""
        decision = {
            "outcome": outcome,
            "payout": payout,
            "reasons": reasons,
            "policy_section": policy_section,
        }
        return call("POST", f"/api/claims/{claim_id}/decision", decision)

    @tool
    def pay_claim(claim_id: str, amount: float) -> str:
        """Pay the approved payout on a claim."""
        return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})

    return [
        get_claim,
        get_policy,
        get_claim_history,
        get_policy_wording,
        record_decision,
        pay_claim,
    ]


def default_model() -> BaseChatModel:
    name = os.environ.get("MODEL_NAME", DEFAULT_MODEL)
    if name == "stub":
        return StubModel()
    return ChatOpenAI(
        model=name,
        base_url=OPENROUTER_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort="medium",
        rate_limiter=rate_limiter,
        max_retries=5,
    )


def money(amount: object) -> str:
    return f"${float(str(amount)):,.2f}"


READ_TITLES = {
    "get_claim": "Read the claim",
    "get_claim_history": "Read the customer's claim history",
    "get_policy_wording": "Read the policy wording",
}


def decision_title(args: dict[str, object], result: str) -> str:
    if result.startswith("Refused"):
        return "Decision refused"
    if args["outcome"] == "approve":
        return f"Decided: approve, {money(args['payout'])}"
    return f"Decided: {args['outcome']}"


def payment_title(args: dict[str, object], result: str) -> str:
    if SIGN_OFF in result:
        return "Payment held for sign-off"
    if result.startswith("Refused"):
        return "Payment refused"
    return f"Paid {money(args['amount'])}"


def step_title(tool_call: ToolCall, result: str) -> str:
    name, args = tool_call["name"], tool_call["args"]
    if name == "get_policy":
        return f"Read policy {args['policy_id']}"
    if name == "record_decision":
        return decision_title(args, result)
    if name == "pay_claim":
        return payment_title(args, result)
    return READ_TITLES.get(name, f"Called {name}")


def record_step(client: httpx.Client, claim_id: str, title: str, detail: str) -> None:
    client.post(
        f"/api/claims/{claim_id}/steps", json={"title": title, "detail": detail}
    )


def record_steps(
    client: httpx.Client,
    claim_id: str,
    messages: list[BaseMessage],
    calls: dict[str, ToolCall],
) -> None:
    for message in messages:
        if isinstance(message, AIMessage):
            calls.update({c["id"] or "": c for c in message.tool_calls})
            if message.text:
                record_step(client, claim_id, "Note", message.text)
        elif isinstance(message, ToolMessage):
            result = message.text
            title = step_title(calls[message.tool_call_id], result)
            record_step(client, claim_id, title, result)


def run(
    claim_id: str,
    thread_id: str,
    model: BaseChatModel | None = None,
    base_url: str = BACKEND_URL,
) -> str:
    """Work one claim and return where it stands afterwards."""
    with connect(base_url) as client:
        return work(client, claim_id, thread_id, model or default_model())


def work(
    client: httpx.Client, claim_id: str, thread_id: str, model: BaseChatModel
) -> str:
    instructions = client.get("/api/instructions").json()["text"]
    client.post(f"/api/claims/{claim_id}/start").raise_for_status()
    agent = create_agent(
        model,
        tools=make_tools(client),
        system_prompt=instructions,
        checkpointer=checkpointer,
    )
    calls: dict[str, ToolCall] = {}
    stopped = "The agent finished without completing the claim."
    try:
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": f"Work claim {claim_id}."}]},
            {"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            for update in chunk.values():
                messages = (update or {}).get("messages", [])
                record_steps(client, claim_id, messages, calls)
    except Exception as error:
        stopped = f"The agent stopped with an error: {error}"
    status = client.get(f"/api/claims/{claim_id}").json()["status"]
    if status == "in_progress":
        record_step(client, claim_id, "Returned to the queue", stopped)
        client.post(f"/api/claims/{claim_id}/reset")
        status = "waiting"
    return status

import os

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
OPENROUTER_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"

checkpointer = InMemorySaver()


@tool
def check_backend() -> str:
    """Check whether the Aegis backend is up."""
    return httpx.get(f"{BACKEND_URL}/api/health").text


def default_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("MODEL_NAME", DEFAULT_MODEL),
        base_url=OPENROUTER_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort="medium",
    )


def run(claim_id: str, thread_id: str, model: BaseChatModel | None = None) -> str:
    """Work one claim and return the agent's final reply."""
    agent = create_agent(
        model or default_model(),
        tools=[check_backend],
        system_prompt="You are the Aegis Agent. Check that the backend is up.",
        checkpointer=checkpointer,
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Work claim {claim_id}."}]},
        {"configurable": {"thread_id": thread_id}},
    )
    return result["messages"][-1].text

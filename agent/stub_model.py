import json
import re
from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool


def tool_call(name: str, args: dict[str, object], step: int) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"stub-{step}"}]
    )


class StubModel(BaseChatModel):
    """A scripted model for tests: it approves the amount claimed, then pays."""

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self.reply(messages))])

    def reply(self, messages: list[BaseMessage]) -> AIMessage:
        request = next(m for m in messages if isinstance(m, HumanMessage))
        claim_id = re.findall(r"CLM-\d+", request.text)[0]
        results = [m for m in messages if isinstance(m, ToolMessage)]
        if not results:
            return tool_call("get_claim", {"claim_id": claim_id}, 1)
        amount = json.loads(results[0].text)["amount_claimed"]
        if len(results) == 1:
            decision = {
                "claim_id": claim_id,
                "outcome": "approve",
                "payout": amount,
                "reasons": "The stub model approves the amount claimed.",
                "policy_section": "Section 10, How we work out your payment",
            }
            return tool_call("record_decision", decision, 2)
        if len(results) == 2:  # noqa: PLR2004
            return tool_call("pay_claim", {"claim_id": claim_id, "amount": amount}, 3)
        return AIMessage(content="The stub model has worked the claim.")

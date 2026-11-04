from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main


class StubModel(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_run_calls_the_backend_and_replies(monkeypatch):
    calls = []

    class Response:
        text = '{"status":"ok"}'

    monkeypatch.setattr(main.httpx, "get", lambda url: calls.append(url) or Response())
    model = StubModel(
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[{"name": "check_backend", "args": {}, "id": "1"}],
                ),
                AIMessage(content="The backend is up."),
            ]
        )
    )

    assert main.run("CLM-001", "thread-1", model) == "The backend is up."
    assert calls == [f"{main.BACKEND_URL}/api/health"]


def test_default_model_uses_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")

    assert main.default_model().model_name == "openrouter/free"

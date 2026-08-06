from trueline.agent import Agent
from trueline.config import Config


class _FakeMessages:
    class _Block:
        type = "text"
        text = "Two files changed. The drop on return_date is critical because it feeds fraud_model_v4 in prod."

    class _Messages:
        async def create(self, **kwargs):
            return _FakeMessages._Response()

    class _Response:
        def __init__(self):
            self.content = [_FakeMessages._Block()]

    def __init__(self):
        self.messages = self._Messages()


def test_summarize_returns_empty_when_no_key(capsys):
    cfg = Config(anthropic_api_key="")
    agent = Agent(cfg)
    result = agent.run_coro(agent.summarize({"verdicts": [], "proposals": []}))
    assert result == ""


def test_summarize_returns_prose(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    cfg = Config()
    agent = Agent(cfg)
    agent._client = _FakeMessages()
    result = agent.run_coro(agent.summarize({"verdicts": [], "proposals": []}))
    assert "fraud_model_v4" in result
from trueline.agent import Agent
from trueline.config import Config


class _FakeOpenAI:
    class _Completions:
        async def create(self, **kwargs):
            return _FakeOpenAI._Response()

    class _Chat:
        def __init__(self, outer):
            self.completions = outer._Completions()

    class _Message:
        content = (
            "Two files changed. The drop on return_date is critical because "
            "it feeds fraud_model_v4 in prod."
        )

    class _Choice:
        def __init__(self):
            self.message = _FakeOpenAI._Message()

    class _Response:
        def __init__(self):
            self.choices = [_FakeOpenAI._Choice()]

    def __init__(self):
        self.chat = self._Chat(self)


def test_summarize_returns_empty_when_no_key():
    cfg = Config(llm_api_key="")
    agent = Agent(cfg)
    result = agent.run_coro(agent.summarize({"verdicts": [], "proposals": []}))
    assert result == ""


def test_summarize_returns_prose(monkeypatch):
    monkeypatch.setenv("GMI_API_KEY", "gmi-fake")
    monkeypatch.setenv("GMI_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
    cfg = Config()
    agent = Agent(cfg)
    agent._client = _FakeOpenAI()
    result = agent.run_coro(agent.summarize({"verdicts": [], "proposals": []}))
    assert "fraud_model_v4" in result

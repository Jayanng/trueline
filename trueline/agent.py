from __future__ import annotations

import asyncio

from .config import Config

_SYSTEM = """You are a data engineering assistant summarizing DataHub lineage impact from a PR diff.

You receive a structured context with verdicts (table, severity, changed columns, affected ML entities) and proposed write-backs (lineage edges to add, glossary terms to propagate).

Write a 2-3 paragraph summary in plain English suitable for a PR comment. Do NOT invent lineage, owners, metrics, or severity — all facts are in the context. If the context is empty or has no ML impact, say so concisely."""


class Agent:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = None
        if cfg.has_anthropic:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)

    def run_coro(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    async def summarize(self, context: dict) -> str:
        if self._client is None:
            return ""
        try:
            msg = await self._client.messages.create(
                model=self.cfg.anthropic_model,
                system=_SYSTEM,
                messages=[{"role": "user", "content": str(context)}],
                max_tokens=500,
            )
            return msg.content[0].text if msg.content else ""
        except Exception:
            return ""
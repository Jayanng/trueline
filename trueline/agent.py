from __future__ import annotations

import asyncio

from .config import Config

_SYSTEM = """You are a data engineering assistant summarizing DataHub lineage impact from a PR diff.

You receive a structured context with verdicts (table, severity, changed columns, affected ML entities) and proposed write-backs (lineage edges to add, glossary terms to propagate).

Write a 2-3 paragraph summary in plain English suitable for a PR comment. Do NOT invent lineage, owners, metrics, or severity — all facts are in the context. If the context is empty or has no ML impact, say so concisely."""


class Agent:
    """Optional LLM prose layer over engine facts (OpenAI-compatible APIs).

    Default target: GMI Cloud (https://api.gmi-serving.com/v1) with
    DeepSeek-V4-Flash. Without an API key the pipeline still works — summarize
    returns "" and comments render from deterministic engine output only.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = None
        if cfg.has_llm:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=cfg.llm_api_key,
                base_url=cfg.llm_base_url,
            )

    def run_coro(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    async def summarize(self, context: dict) -> str:
        if self._client is None:
            return ""
        try:
            msg = await self._client.chat.completions.create(
                model=self.cfg.llm_model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": str(context)},
                ],
                max_tokens=500,
            )
            choice = msg.choices[0].message if msg.choices else None
            return (choice.content or "").strip() if choice else ""
        except Exception:
            return ""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DATASET_URN = re.compile(
    r"^urn:li:dataset:\(urn:li:dataPlatform:([^,()]+),([^,()]+),(PROD|DEV|TEST|STAGING)\)$"
)


@dataclass(frozen=True)
class TableRef:
    platform: str
    db: str
    schema: str
    table: str
    env: str = "PROD"

    @property
    def qualified(self) -> str:
        # Skip empty segments so schema="" yields "db.table", not "db..table".
        return ".".join(p for p in (self.db, self.schema, self.table) if p)

    @property
    def urn(self) -> str:
        return f"urn:li:dataset:(urn:li:dataPlatform:{self.platform},{self.qualified},{self.env})"


def parse_dataset_urn(urn: str) -> TableRef:
    match = _DATASET_URN.match(urn)
    if not match:
        raise ValueError(f"not a dataset urn: {urn}")
    platform, qualified, env = match.groups()
    parts = qualified.split(".")
    if len(parts) == 3:
        db, schema, table = parts
    elif len(parts) == 2:
        db, table = parts
        schema = ""
    else:
        db, schema, table = "", "", qualified
    return TableRef(platform=platform, db=db, schema=schema, table=table, env=env)


def _env_first(*keys: str, default: str = "") -> str:
    for key in keys:
        val = os.getenv(key)
        if val:
            return val
    return default


@dataclass(frozen=True)
class Config:
    gms_url: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"))
    gms_token: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_TOKEN", ""))
    mcp_url: str = field(default_factory=lambda: os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"))
    # Optional LLM prose layer — OpenAI-compatible (default: GMI Cloud + DeepSeek V4 Flash).
    # Prefer GMI_*; LLM_* and legacy ANTHROPIC_* still accepted.
    llm_api_key: str = field(
        default_factory=lambda: _env_first("GMI_API_KEY", "LLM_API_KEY", "ANTHROPIC_API_KEY")
    )
    llm_base_url: str = field(
        default_factory=lambda: _env_first(
            "GMI_BASE_URL",
            "LLM_BASE_URL",
            default="https://api.gmi-serving.com/v1",
        )
    )
    llm_model: str = field(
        default_factory=lambda: _env_first(
            "GMI_MODEL",
            "LLM_MODEL",
            "ANTHROPIC_MODEL",
            default="deepseek-ai/DeepSeek-V4-Flash",
        )
    )
    dry_run: bool = field(
        default_factory=lambda: os.getenv("TRUELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")
    )
    state_db: Path = field(default_factory=lambda: Path(os.getenv("TRUELINE_STATE_DB", ".trueline/state.db")))
    contracts_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("TRUELINE_CONTRACTS_PATH", "contracts/model-change-contracts.json")
        )
    )

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_api_key)

    # Backward-compatible aliases (older tests / docs).
    @property
    def has_anthropic(self) -> bool:
        return self.has_llm

    @property
    def anthropic_api_key(self) -> str:
        return self.llm_api_key

    @property
    def anthropic_model(self) -> str:
        return self.llm_model


def load_table_map(path: Path) -> dict[str, TableRef]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, TableRef] = {}
    for key, value in data.items():
        out[key] = TableRef(
            platform=value["platform"],
            db=value["db"],
            schema=value["schema"],
            table=value["table"],
            env=value.get("env", "PROD"),
        )
    return out

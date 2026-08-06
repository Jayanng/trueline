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
        return f"{self.db}.{self.schema}.{self.table}"

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
    else:
        db, schema, table = "", "", qualified
    return TableRef(platform=platform, db=db, schema=schema, table=table, env=env)


@dataclass(frozen=True)
class Config:
    gms_url: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"))
    gms_token: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_TOKEN", ""))
    mcp_url: str = field(default_factory=lambda: os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    dry_run: bool = field(
        default_factory=lambda: os.getenv("TRUELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")
    )
    state_db: Path = field(default_factory=lambda: Path(os.getenv("TRUELINE_STATE_DB", ".trueline/state.db")))

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


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
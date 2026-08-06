from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.client import HTTPConnection
from typing import Any

from datahub.metadata.urns import DatasetUrn, GlossaryTermUrn
from datahub.sdk import DataHubClient

from .config import Config, TableRef


@dataclass(frozen=True)
class LineageResult:
    urn: str
    entity_type: str
    platform: str
    name: str
    hops: int
    paths: tuple[tuple[str, ...], ...] = ()


def _mcp_call(mcp_url: str, method: str, params: dict[str, Any] | None = None) -> Any:
    host, port, path = "127.0.0.1", 8000, "/mcp"
    if mcp_url.startswith("http"):
        rest = mcp_url.split("://", 1)[1]
        host, _, rest = rest.partition(":")
        port = int(rest.split("/")[0]) if rest else 8000
    conn = HTTPConnection(host, port, timeout=10)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    conn.request("POST", path, body=body,
                 headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    resp = conn.getresponse()
    raw = resp.read().decode()
    conn.close()
    for line in raw.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise RuntimeError(f"MCP call failed: {raw[:200]}")


class DataHubGateway:
    """Reads via MCP server, writes via SDK.

    MCP server must be running at cfg.mcp_url (started as a sidecar).
    The SDK client is used for writes only (add_lineage, add_term).
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.mcp_url = getattr(cfg, "mcp_url", os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"))
        self._client = DataHubClient(server=cfg.gms_url, token=cfg.gms_token)

    def _mcp(self, tool: str, args: dict[str, Any] | None = None) -> Any:
        result = _mcp_call(self.mcp_url, "tools/call", {"name": tool, "arguments": args or {}})
        if "result" in result and result["result"]["content"]:
            text = result["result"]["content"][0].get("text", "{}")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
            return text
        return {}

    def search(self, query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]:
        data = self._mcp("search", {"query": query})
        entities = data.get("entities", [])
        return [e["urn"] for e in entities if entity_type in e.get("type", "")][:limit]

    def entity(self, urn: str) -> dict:
        data = self._mcp("get_entities", {"urns": [urn]})
        if isinstance(data, list):
            return data[0] if data else {"urn": urn}
        return data.get("entities", [{}])[0] if "entities" in data else {"urn": urn}

    def owners(self, urn: str) -> list[str]:
        ent = self.entity(urn)
        owners_list = ent.get("owners", []) or []
        return sorted(set(o.get("owner", "") for o in owners_list if o.get("owner")))

    def environment(self, urn: str) -> str:
        ent = self.entity(urn)
        props = ent.get("customProperties", {}) or {}
        return str(props.get("environment", ""))

    def downstream(self, ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]:
        data = self._mcp("get_lineage", {
            "urn": ref.urn,
            "upstream": False,
            "max_hops": max_hops,
        })
        entities = data.get("entities", []) if isinstance(data, dict) else data
        out: list[LineageResult] = []
        for e in entities:
            urn = e.get("urn", "")
            hops = e.get("hops", 1)
            out.append(LineageResult(
                urn=urn,
                entity_type=e.get("type", "dataset"),
                platform=e.get("platform", ""),
                name=e.get("name", urn.split(":")[-1]),
                hops=hops,
                paths=tuple(tuple(p) for p in (e.get("paths", []) or [])),
            ))
        return out

    def column_terms(self, ref: TableRef, column: str) -> list[str]:
        try:
            ent = self._client.entities.get(ref.urn)
            col = ent.get(column)
            if col is None:
                return []
            getter = getattr(col, "get_glossary_terms", None)
            if getter is None:
                return []
            terms = getter()
            return [str(t) for t in (terms or [])]
        except Exception:
            return []

    def add_lineage(self, upstream: TableRef, downstream: TableRef,
                    column_lineage: dict[str, list[str]] | None = None, wait: bool = False) -> None:
        self._client.lineage.add_lineage(
            upstream=DatasetUrn.from_string(upstream.urn),
            downstream=DatasetUrn.from_string(downstream.urn),
            column_lineage=column_lineage,
            emit_mode="SYNC_WAIT" if wait else "SYNC_PRIMARY",
        )

    def add_term(self, ref: TableRef, column: str, term_urn: str) -> None:
        ent = self._client.entities.get(ref.urn)
        ent[column].add_term(GlossaryTermUrn.from_string(term_urn))
        self._client.entities.update(ent)
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from http.client import HTTPConnection
from typing import Any
from urllib.parse import urlparse

from datahub.metadata.urns import DatasetUrn, GlossaryTermUrn
from datahub.sdk import DataHubClient

from .config import Config, TableRef

_ML_URN_PREFIXES = (
    "urn:li:mlFeature:",
    "urn:li:mlModel:",
    "urn:li:mlModelGroup:",
    "urn:li:mlFeatureTable:",
    "urn:li:mlPrimaryKey:",
    "urn:li:mlModelDeployment:",
)

# mcp-server-datahub get_lineage returns empty when max_hops > 2 on current Core.
_MCP_MAX_HOPS = 2


@dataclass(frozen=True)
class LineageResult:
    urn: str
    entity_type: str
    platform: str
    name: str
    hops: int
    paths: tuple[tuple[str, ...], ...] = ()


def _mcp_call(mcp_url: str, method: str, params: dict[str, Any] | None = None) -> Any:
    parsed = urlparse(mcp_url if "://" in mcp_url else f"http://{mcp_url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    path = parsed.path or "/mcp"
    conn = HTTPConnection(host, port, timeout=30)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    conn.request(
        "POST",
        path,
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    resp = conn.getresponse()
    raw = resp.read().decode()
    conn.close()
    for line in raw.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MCP call failed: {raw[:200]}") from exc


def _entity_type_from_urn(urn: str) -> str:
    if urn.startswith("urn:li:dataset:"):
        return "dataset"
    if urn.startswith("urn:li:mlFeature:"):
        return "mlfeature"
    if urn.startswith("urn:li:mlModelGroup:"):
        return "mlmodelgroup"
    if urn.startswith("urn:li:mlModel:"):
        return "mlmodel"
    if urn.startswith("urn:li:mlFeatureTable:"):
        return "mlfeaturetable"
    if urn.startswith("urn:li:mlPrimaryKey:"):
        return "mlprimarykey"
    if urn.startswith("urn:li:mlModelDeployment:"):
        return "mlmodeldeployment"
    return "unknown"


def _name_from_urn(urn: str) -> str:
    """Best-effort display name from a DataHub URN."""
    if "(" in urn and urn.endswith(")"):
        inner = urn[urn.index("(") + 1 : -1]
        # mlModel / mlModelGroup: (platformUrn, name, env)
        if urn.startswith("urn:li:mlModel:") or urn.startswith("urn:li:mlModelGroup:"):
            parts = inner.split(",")
            if len(parts) >= 2:
                return parts[1]
        # mlFeature: (namespace, name)
        if urn.startswith("urn:li:mlFeature:"):
            parts = inner.split(",")
            return parts[-1] if parts else urn
        # dataset: (platformUrn, qualifiedName, env)
        if urn.startswith("urn:li:dataset:"):
            parts = inner.split(",")
            if len(parts) >= 2:
                return parts[1].rsplit(".", 1)[-1]
    return urn.rsplit(":", 1)[-1]


def _flatten_search_results(data: Any) -> list[dict]:
    """Normalize MCP search / lineage payloads into a list of entity-ish dicts.

    Live mcp-server-datahub shapes observed:
      search:     { searchResults: [ { entity: { urn, type, ... } }, ... ], total }
      get_lineage:{ downstreams|upstreams: { searchResults: [ { entity, degree } ], total } }
    """
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if not isinstance(data, dict):
        return []

    # Direct searchResults (search tool)
    if isinstance(data.get("searchResults"), list):
        return _rows_from_search_results(data["searchResults"])

    # Nested under downstreams / upstreams (get_lineage)
    for key in ("downstreams", "upstreams"):
        block = data.get(key)
        if isinstance(block, dict) and isinstance(block.get("searchResults"), list):
            return _rows_from_search_results(block["searchResults"])

    # Older / alternate shapes
    for key in ("entities", "results", "lineage", "items"):
        if isinstance(data.get(key), list):
            return [x for x in data[key] if isinstance(x, dict)]

    if "urn" in data:
        return [data]
    return []


def _rows_from_search_results(rows: list) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ent = row.get("entity") if isinstance(row.get("entity"), dict) else row
        if not isinstance(ent, dict):
            continue
        # Promote degree/hops onto the entity dict for lineage parsing.
        merged = dict(ent)
        if "degree" in row and "hops" not in merged and "degree" not in merged:
            merged["degree"] = row["degree"]
        if "hops" in row and "hops" not in merged:
            merged["hops"] = row["hops"]
        out.append(merged)
    return out


class DataHubGateway:
    """Reads via MCP + SDK (live catalog only), writes via SDK.

    MCP server must be running at cfg.mcp_url (started as a sidecar).
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.mcp_url = getattr(cfg, "mcp_url", os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp"))
        self._client = DataHubClient(server=cfg.gms_url, token=cfg.gms_token)

    def _mcp(self, tool: str, args: dict[str, Any] | None = None) -> Any:
        result = _mcp_call(self.mcp_url, "tools/call", {"name": tool, "arguments": args or {}})
        if isinstance(result, dict) and result.get("error"):
            return {"error": result["error"], "text": str(result["error"])}
        if "result" in result and result["result"]:
            # Prefer structuredContent when present (same data, already parsed).
            structured = result["result"].get("structuredContent")
            if structured is not None and structured != {}:
                # Some tools wrap under {"result": ...}
                if isinstance(structured, dict) and "result" in structured and len(structured) == 1:
                    return structured["result"]
                return structured
            content = result["result"].get("content") or []
            if content:
                text = content[0].get("text", "{}")
                if isinstance(text, str):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"text": text}
                return text
        return {}

    def search(self, query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]:
        data = self._mcp("search", {"query": query, "num_results": min(limit, 50)})
        rows = _flatten_search_results(data)
        out: list[str] = []
        type_filter = (entity_type or "").lower()
        for e in rows:
            urn = e.get("urn", "")
            if not urn:
                continue
            etype = str(e.get("type", e.get("entityType", ""))).lower()
            if type_filter:
                if type_filter == "ml":
                    if not urn.startswith(_ML_URN_PREFIXES):
                        continue
                elif type_filter == "dataset":
                    if not urn.startswith("urn:li:dataset:"):
                        continue
                elif type_filter not in etype and type_filter not in urn.lower():
                    continue
            out.append(urn)
            if len(out) >= limit:
                break
        return out

    def entity(self, urn: str) -> dict:
        data = self._mcp("get_entities", {"urns": [urn]})
        rows = _flatten_search_results(data) if not isinstance(data, list) else [
            x for x in data if isinstance(x, dict)
        ]
        if rows:
            # Prefer exact urn match when multiple returned.
            for r in rows:
                if r.get("urn") == urn and "error" not in r:
                    return r
            if "error" not in rows[0]:
                return rows[0]
        if isinstance(data, dict) and urn in data:
            ent = data[urn]
            return ent if isinstance(ent, dict) else {"urn": urn, "raw": ent}
        return {"urn": urn}

    def owners(self, urn: str) -> list[str]:
        ent = self.entity(urn)
        owners_list = (
            ent.get("owners")
            or (ent.get("ownership") or {}).get("owners")
            or (ent.get("properties") or {}).get("owners")
            or []
        )
        names: set[str] = set()
        for o in owners_list:
            if isinstance(o, str):
                owner = o
            elif isinstance(o, dict):
                owner = o.get("owner") or o.get("urn") or ""
            else:
                continue
            if not owner:
                continue
            if owner.startswith("urn:li:corpuser:"):
                names.add(owner.split(":")[-1])
            else:
                names.add(owner)
        return sorted(names)

    def environment(self, urn: str) -> str:
        ent = self.entity(urn)
        props = ent.get("customProperties") or {}
        if isinstance(props, dict) and props.get("environment"):
            return str(props["environment"])
        for key in ("properties", "mlModelProperties", "datasetProperties"):
            nested = ent.get(key) or {}
            if isinstance(nested, dict):
                cp = nested.get("customProperties") or {}
                if isinstance(cp, dict) and cp.get("environment"):
                    return str(cp["environment"])
        return ""

    def downstream(self, ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]:
        """Walk real downstream lineage from the live DataHub catalog.

        Prefer the Python SDK (reliable multi-hop). Also query MCP get_lineage
        (upstream=False) with hops capped at 2 — higher values return empty on
        current mcp-server-datahub/Core. Expand ML aspect edges only when the
        live entity aspects declare them (sources / mlFeatures / groups).
        """
        out = self._sdk_downstream(ref, column=column, max_hops=max_hops)

        mcp_hops = min(max_hops, _MCP_MAX_HOPS)
        args: dict[str, Any] = {
            "urn": ref.urn,
            "upstream": False,
            "max_hops": mcp_hops,
            "max_results": 50,
        }
        if column:
            args["column"] = column
        data = self._mcp("get_lineage", args)
        out = self._merge_lineage(out, self._parse_lineage_entities(_flatten_search_results(data)))

        # Expand ML from the source and every real downstream dataset hop.
        bases = [ref.urn] + [r.urn for r in out if r.urn.startswith("urn:li:dataset:")]
        for base in dict.fromkeys(bases):
            out = self._merge_lineage(
                out,
                self._ml_aspect_edges(base, known=out, max_hops=max_hops),
            )
        return out

    def _sdk_downstream(
        self, ref: TableRef, column: str | None = None, max_hops: int = 4
    ) -> list[LineageResult]:
        try:
            kwargs: dict[str, Any] = {
                "source_urn": DatasetUrn.from_string(ref.urn),
                "direction": "downstream",
                "max_hops": max_hops,
            }
            if column:
                kwargs["source_column"] = column
            results = self._client.lineage.get_lineage(**kwargs)
        except Exception:
            return []
        out: list[LineageResult] = []
        for r in results or []:
            urn = str(getattr(r, "urn", "") or "")
            if not urn:
                continue
            paths = getattr(r, "paths", None) or ()
            path_tuples: list[tuple[str, ...]] = []
            for p in paths:
                if isinstance(p, (list, tuple)):
                    path_tuples.append(tuple(str(x) for x in p))
            out.append(LineageResult(
                urn=urn,
                entity_type=str(
                    getattr(r, "type", None)
                    or getattr(r, "entity_type", None)
                    or _entity_type_from_urn(urn)
                ).lower(),
                platform=str(getattr(r, "platform", "") or ""),
                name=str(getattr(r, "name", None) or _name_from_urn(urn)),
                hops=int(getattr(r, "hops", 1) or 1),
                paths=tuple(path_tuples),
            ))
        return out

    def _parse_lineage_entities(self, entities: list) -> list[LineageResult]:
        out: list[LineageResult] = []
        for e in entities:
            if not isinstance(e, dict):
                continue
            urn = e.get("urn", "")
            if not urn:
                continue
            hops = int(e.get("hops", e.get("degree", 1)) or 1)
            paths_raw = e.get("paths") or e.get("path") or []
            paths: list[tuple[str, ...]] = []
            if paths_raw and isinstance(paths_raw[0], str):
                paths = [tuple(paths_raw)]
            else:
                for p in paths_raw:
                    if isinstance(p, (list, tuple)):
                        paths.append(tuple(str(x) for x in p))
                    elif isinstance(p, dict) and "path" in p:
                        paths.append(tuple(str(x) for x in p["path"]))
            out.append(LineageResult(
                urn=urn,
                entity_type=str(
                    e.get("type", e.get("entityType", _entity_type_from_urn(urn)))
                ).lower(),
                platform=str(e.get("platform", "") if not isinstance(e.get("platform"), dict)
                             else e.get("platform", {}).get("name", "")),
                name=str(e.get("name", _name_from_urn(urn))),
                hops=hops,
                paths=tuple(paths),
            ))
        return out

    def _merge_lineage(self, base: list[LineageResult], extra: list[LineageResult]) -> list[LineageResult]:
        seen = {r.urn for r in base}
        merged = list(base)
        for r in extra:
            if r.urn not in seen:
                merged.append(r)
                seen.add(r.urn)
        return merged

    def _ml_aspect_edges(
        self,
        source_urn: str,
        known: list[LineageResult],
        max_hops: int = 4,
    ) -> list[LineageResult]:
        """Follow real ML aspect links declared on live entities only."""
        out: list[LineageResult] = []
        candidates = [r.urn for r in known]
        short = _dataset_short_name(source_urn)
        queries = [q for q in (short, "*") if q]
        for q in queries:
            try:
                candidates.extend(self.search(query=q, entity_type="ml", limit=50))
                candidates.extend(self.search(query=q, entity_type="", limit=50))
            except Exception:
                continue

        feature_urns: list[str] = []
        for urn in dict.fromkeys(candidates):
            if not urn.startswith("urn:li:mlFeature:"):
                continue
            sources = self._extract_urn_list(self.entity(urn), ("sources",))
            if source_urn not in sources:
                continue
            feature_urns.append(urn)
            out.append(LineageResult(
                urn=urn,
                entity_type="mlfeature",
                platform="",
                name=_name_from_urn(urn),
                hops=1,
                paths=((source_urn, urn),),
            ))

        if max_hops < 2 or not feature_urns:
            return out

        model_candidates = list(candidates)
        for q in queries:
            try:
                model_candidates.extend(self.search(query=q, entity_type="ml", limit=50))
            except Exception:
                continue

        for m_urn in dict.fromkeys(model_candidates):
            if not m_urn.startswith("urn:li:mlModel:"):
                continue
            ent = self.entity(m_urn)
            if ent.get("error"):
                continue
            model_features = self._extract_urn_list(ent, ("mlFeatures", "features"))
            linked = [f for f in feature_urns if f in model_features]
            if not linked:
                continue
            f0 = linked[0]
            out.append(LineageResult(
                urn=m_urn,
                entity_type="mlmodel",
                platform="",
                name=_name_from_urn(m_urn),
                hops=2,
                paths=((source_urn, f0, m_urn),),
            ))
            if max_hops < 3:
                continue
            for g_urn in self._extract_urn_list(ent, ("groups", "group")):
                if not g_urn.startswith("urn:li:mlModelGroup:"):
                    continue
                out.append(LineageResult(
                    urn=g_urn,
                    entity_type="mlmodelgroup",
                    platform="",
                    name=_name_from_urn(g_urn),
                    hops=3,
                    paths=((source_urn, f0, m_urn, g_urn),),
                ))
        return out

    @staticmethod
    def _extract_urn_list(ent: dict, keys: tuple[str, ...]) -> list[str]:
        buckets: list[Any] = []
        for key in keys:
            if key in ent:
                buckets.append(ent[key])
            for nest in ("properties", "mlFeatureProperties", "mlModelProperties"):
                nested = ent.get(nest) or {}
                if isinstance(nested, dict) and key in nested:
                    buckets.append(nested[key])
        urns: list[str] = []
        for bucket in buckets:
            if isinstance(bucket, str):
                urns.append(bucket)
            elif isinstance(bucket, list):
                for item in bucket:
                    if isinstance(item, str):
                        urns.append(item)
                    elif isinstance(item, dict) and item.get("urn"):
                        urns.append(str(item["urn"]))
        return urns

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


def _dataset_short_name(urn: str) -> str:
    """Extract the table short name from a dataset URN (last dotted segment)."""
    if not urn.startswith("urn:li:dataset:"):
        return _name_from_urn(urn)
    try:
        inner = urn[len("urn:li:dataset:(") : -1] if urn.endswith(")") else urn
        parts = inner.split(",")
        if len(parts) >= 2:
            return parts[1].rsplit(".", 1)[-1]
    except Exception:
        pass
    return _name_from_urn(urn)

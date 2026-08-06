from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot

from .config import TableRef, parse_dataset_urn
from .datahub_client import DataHubGateway
from .diff_parser import ChangedFile
from .state import StateStore
from .warnings import CatalogWarning, empty_lineage_mapping_refused


def _mapping_is_usable(mapping: dict | None) -> bool:
    """True only if at least one downstream col maps to a non-empty upstream list."""
    if not mapping or not isinstance(mapping, dict):
        return False
    for _down, ups in mapping.items():
        if ups and any(str(u).strip() for u in ups):
            return True
    return False

_JINJA_REF = re.compile(r"{{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*}}")
_JINJA_OTHER = re.compile(r"{{.*?}}", re.DOTALL)


def normalize_jinja(sql: str) -> str:
    sql = _JINJA_REF.sub(r"\1", sql)
    return _JINJA_OTHER.sub("", sql)


def _base_table(select: sqlglot.exp.Select) -> str | None:
    from_ = select.find(sqlglot.exp.From)
    if from_ is None or not isinstance(from_.this, sqlglot.exp.Table):
        return None
    return from_.this.name


def derive_column_mapping(query: str, upstream: TableRef) -> dict[str, list[str]]:
    """Output column -> upstream columns, FROM-aware: bare columns bind to the
    statement's base table; qualified columns bind to their own table."""
    mapping: dict[str, list[str]] = {}
    for stmt in sqlglot.parse(normalize_jinja(query)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        base = _base_table(select)
        for expr in select.expressions:
            alias = expr.alias_or_name
            if isinstance(expr, sqlglot.exp.Column):
                if expr.table or (base and base.lower() == upstream.table.lower()):
                    mapping[alias] = [expr.name]
                continue
            cols = sorted({
                c.name for c in expr.find_all(sqlglot.exp.Column)
                if (c.table and c.table.lower() == upstream.table.lower())
                or (not c.table and base and base.lower() == upstream.table.lower())
            })
            if cols:
                mapping[alias] = cols
    return mapping


@dataclass(frozen=True)
class Proposal:
    kind: str  # LINEAGE | GLOSSARY_TERM
    target_urn: str
    detail: dict
    source: str


def _from_tables(select: sqlglot.exp.Select) -> list[str]:
    tables: list[str] = []
    for from_ in select.find_all(sqlglot.exp.From):
        if isinstance(from_.this, sqlglot.exp.Table):
            tables.append(from_.this.name)
    return tables


async def plan_writebacks(
    file: ChangedFile, ref: TableRef, sql: str, gateway: DataHubGateway, source: str
) -> list[Proposal]:
    if not sql:
        return []
    proposals: list[Proposal] = []
    for stmt in sqlglot.parse(normalize_jinja(sql)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        for table_name in _from_tables(select):
            if table_name.lower() == ref.table.lower():
                continue
            upstream = TableRef(platform=ref.platform, db=ref.db, schema=ref.schema, table=table_name, env=ref.env)
            mapping = derive_column_mapping(sql, upstream)
            if not mapping:
                continue
            missing: dict[str, list[str]] = {}
            for down_col, up_cols in mapping.items():
                present = any(
                    r.urn == ref.urn
                    for up_col in up_cols
                    for r in gateway.downstream(upstream, column=up_col, max_hops=1)
                )
                if not present:
                    missing[down_col] = up_cols
            if missing:
                proposals.append(
                    Proposal(
                        kind="LINEAGE",
                        target_urn=ref.urn,
                        detail={"upstream": upstream.urn, "mapping": missing},
                        source=source,
                    )
                )
    return proposals


async def plan_term_drift(
    file: ChangedFile, ref: TableRef, sql: str, gateway: DataHubGateway, source: str
) -> list[Proposal]:
    if not sql:
        return []
    proposals: list[Proposal] = []
    for stmt in sqlglot.parse(normalize_jinja(sql)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        for expr in select.expressions:
            alias = expr.alias_or_name
            for col in expr.find_all(sqlglot.exp.Column):
                if not col.table:
                    continue
                up_ref = TableRef(platform=ref.platform, db=ref.db, schema=ref.schema, table=col.table, env=ref.env)
                up_terms = gateway.column_terms(up_ref, col.name)
                pii_terms = [t for t in up_terms if "pii" in t.lower()]
                if not pii_terms:
                    continue
                down_terms = gateway.column_terms(ref, alias)
                if any("pii" in t.lower() for t in down_terms):
                    continue
                proposals.append(
                    Proposal(
                        kind="GLOSSARY_TERM",
                        target_urn=ref.urn,
                        detail={"column": alias, "term": pii_terms[0], "upstream": up_ref.urn},
                        source=source,
                    )
                )
    return proposals


async def apply_proposals(
    proposals: list[Proposal],
    gateway: DataHubGateway,
    state: StateStore,
    run_id: str,
) -> list[tuple[Proposal, str, CatalogWarning | None]]:
    """Apply proposals. Never commit empty column lineage (silent graph wipe risk).

    Returns (proposal, status, optional warning). Status is one of:
    COMMITTED | SKIPPED | BLOCKED_EMPTY.
    """
    results: list[tuple[Proposal, str, CatalogWarning | None]] = []
    for p in proposals:
        if await state.proposal_status(p.kind, p.target_urn, p.detail) == "COMMITTED":
            results.append((p, "SKIPPED", None))
            continue
        if p.kind == "LINEAGE":
            mapping = p.detail.get("mapping") if isinstance(p.detail, dict) else None
            if not _mapping_is_usable(mapping):
                warn = empty_lineage_mapping_refused(
                    p.target_urn,
                    str((p.detail or {}).get("upstream", "")),
                )
                results.append((p, "BLOCKED_EMPTY", warn))
                continue
        if p.kind == "LINEAGE":
            upstream = parse_dataset_urn(p.detail["upstream"])
            downstream = parse_dataset_urn(p.target_urn)
            column_lineage = {
                k: list(v) for k, v in p.detail["mapping"].items() if v
            }
            if not _mapping_is_usable(column_lineage):
                warn = empty_lineage_mapping_refused(p.target_urn, upstream.urn)
                results.append((p, "BLOCKED_EMPTY", warn))
                continue
            gateway.add_lineage(
                upstream=upstream,
                downstream=downstream,
                column_lineage=column_lineage,
                wait=True,
            )
        elif p.kind == "GLOSSARY_TERM":
            gateway.add_term(
                ref=parse_dataset_urn(p.target_urn),
                column=p.detail["column"],
                term_urn=p.detail["term"],
            )
        else:  # pragma: no cover - future kinds must be handled explicitly
            raise ValueError(f"unknown proposal kind: {p.kind}")
        proposal_id = await state.add_proposal(run_id, p.kind, p.target_urn, p.detail)
        if proposal_id:
            await state.set_status(proposal_id, "COMMITTED")
        else:
            await state.set_status_for(p.kind, p.target_urn, p.detail, "COMMITTED")
        results.append((p, "COMMITTED", None))
    return results
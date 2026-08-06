"""Structured catalog warnings — refuse silent empty success.

Inspired by DataHub dbt connector silent lineage-drop failures: when the graph
or artifact workflow is wrong, name the entity and the remedy loudly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CatalogWarning:
    code: str
    urn: str
    message: str
    remedy: str

    def to_dict(self) -> dict:
        return asdict(self)


def no_ml_lineage(urn: str, table: str) -> CatalogWarning:
    return CatalogWarning(
        code="NO_ML_LINEAGE",
        urn=urn,
        message=(
            f"No ML entity downstream of `{table}` ({urn}). "
            "Severity may understate production risk if the catalog/map is wrong."
        ),
        remedy=(
            "Confirm demo_repo/table_map.json URN casing; run python seed/verify_graph.py; "
            "ensure MCP is up and DATAHUB_GMS_* are set; re-seed ML tail if needed."
        ),
    )


def no_downstream_at_all(urn: str, table: str) -> CatalogWarning:
    return CatalogWarning(
        code="NO_DOWNSTREAM",
        urn=urn,
        message=(
            f"No downstream entities from `{table}` ({urn}). "
            "Empty lineage can mean wrong URN, MCP/GMS failure, or a real leaf table."
        ),
        remedy=(
            "Check MCP (MCP_SERVER_URL) and GMS token; search the table in DataHub UI; "
            "fix table_map.json; do not treat empty as 'safe to merge' without confirmation."
        ),
    )


def empty_lineage_mapping_refused(target_urn: str, upstream: str) -> CatalogWarning:
    return CatalogWarning(
        code="EMPTY_LINEAGE_REFUSED",
        urn=target_urn,
        message=(
            f"Refused lineage write to {target_urn} from {upstream}: empty column mapping. "
            "Writing empty fine-grained lineage can replace richer edges from a prior good run."
        ),
        remedy=(
            "Ensure PR head SQL is readable via git show <head>:<path>; fix sqlglot mapping; "
            "never commit table-only overwrites when column map is empty."
        ),
    )


def unmapped_sql_file(path: str) -> CatalogWarning:
    return CatalogWarning(
        code="UNMAPPED_SQL_FILE",
        urn="",
        message=f"SQL file not in table_map: {path} — skipped (no verdict).",
        remedy="Add the path to demo_repo/table_map.json with the exact DataHub dataset URN parts.",
    )

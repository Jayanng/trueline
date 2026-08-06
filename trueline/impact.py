from __future__ import annotations

from dataclasses import dataclass

from .config import TableRef
from .datahub_client import LineageResult
from .diff_parser import ChangeKind, ChangedColumn, ChangedFile
from .ml_impact import find_ml_impacts

DASHBOARD_PLATFORMS = frozenset({"looker", "tableau", "powerbi", "superset"})


@dataclass(frozen=True)
class AffectedEntity:
    urn: str
    name: str
    kind: str
    owner: str | None
    reason: str


@dataclass(frozen=True)
class TableVerdict:
    ref: TableRef
    file_path: str
    columns: tuple[ChangedColumn, ...]
    severity: str
    affected: tuple[AffectedEntity, ...]
    message: str


def _ml_message(file: ChangedFile, ml) -> str:
    drops = [c.name for c in file.columns if c.kind == ChangeKind.DROP]
    models = [i for i in ml if i.kind == "MLMODEL"]
    deploys = [i for i in ml if i.kind == "MLMODELDEPLOYMENT"]
    model_bit = models[0].name if models else (ml[0].name if ml else "ML entity")
    env_bit = ""
    if models and models[0].env:
        env_bit = f" [{models[0].env}]"
    elif deploys and deploys[0].env:
        env_bit = f" [{deploys[0].env}]"
    if drops:
        return (
            f"silent prod-model breakage — dropping {', '.join(drops)} "
            f"reaches {model_bit}{env_bit} via ML lineage"
        )
    return f"silent prod-model breakage — change reaches {model_bit}{env_bit} via ML lineage"


def compute_verdict(
    ref: TableRef,
    file: ChangedFile,
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> TableVerdict:
    ml = find_ml_impacts(results, owners_by_urn, env_by_urn)
    if ml:
        affected = tuple(
            AffectedEntity(
                i.urn,
                i.name,
                i.kind,
                i.owner,
                (
                    f"downstream ML path hops={len(i.path) or i.kind}"
                    if i.path
                    else "downstream ML entity"
                ),
            )
            for i in ml
        )
        return TableVerdict(
            ref,
            file.file_path,
            file.columns,
            "CRITICAL",
            affected,
            _ml_message(file, ml),
        )
    dashboards = [r for r in results if r.platform.lower() in DASHBOARD_PLATFORMS]
    if dashboards:
        affected = tuple(
            AffectedEntity(r.urn, r.name, "DASHBOARD", None, "downstream BI consumer") for r in dashboards
        )
        return TableVerdict(ref, file.file_path, file.columns, "HIGH", affected, "downstream dashboards/BI consumers")
    if len(results) > 1:
        affected = tuple(
            AffectedEntity(r.urn, r.name, r.entity_type.upper() or "DATASET", None, "downstream")
            for r in results
        )
        return TableVerdict(ref, file.file_path, file.columns, "MEDIUM", affected, "multiple downstream consumers")
    if all(c.kind == ChangeKind.ADD for c in file.columns):
        return TableVerdict(ref, file.file_path, file.columns, "LOW", (), "additive change only")
    return TableVerdict(ref, file.file_path, file.columns, "MEDIUM", (), "non-additive change, no ML/dashboard consumers")

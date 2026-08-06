from __future__ import annotations

from dataclasses import dataclass, field

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
class WhyRule:
    """Machine-readable severity trail entry (no invented metrics)."""
    rule: str
    urn: str
    kind: str
    hops: int
    detail: str = ""


@dataclass(frozen=True)
class TableVerdict:
    ref: TableRef
    file_path: str
    columns: tuple[ChangedColumn, ...]
    severity: str
    affected: tuple[AffectedEntity, ...]
    message: str
    why: tuple[WhyRule, ...] = field(default_factory=tuple)
    column_suspects: tuple[str, ...] = field(default_factory=tuple)


def _ml_message(file: ChangedFile, ml, *, critical: bool) -> str:
    drops = [c.name for c in file.columns if c.kind == ChangeKind.DROP]
    models = [i for i in ml if i.kind == "MLMODEL"]
    deploys = [i for i in ml if i.kind == "MLMODELDEPLOYMENT"]
    model_bit = models[0].name if models else (ml[0].name if ml else "ML entity")
    env_bit = ""
    if models and models[0].env:
        env_bit = f" [{models[0].env}]"
    elif deploys and deploys[0].env:
        env_bit = f" [{deploys[0].env}]"
    if not critical:
        return (
            f"additive change only — ML consumers exist ({model_bit}{env_bit}) "
            f"but no DROP/TYPE_CHANGE (no silent breakage)"
        )
    if drops:
        return (
            f"silent prod-model breakage — dropping {', '.join(drops)} "
            f"reaches {model_bit}{env_bit} via ML lineage"
        )
    return f"silent prod-model breakage — change reaches {model_bit}{env_bit} via ML lineage"


def _column_suspects(file: ChangedFile) -> tuple[str, ...]:
    """DROPs / TYPE_CHANGEs are the columns most likely to break features."""
    return tuple(
        c.name for c in file.columns
        if c.kind in (ChangeKind.DROP, ChangeKind.TYPE_CHANGE)
    )


def _ml_why(ml, rule: str) -> tuple[WhyRule, ...]:
    return tuple(
        WhyRule(
            rule=rule,
            urn=i.urn,
            kind=i.kind,
            hops=i.hops,
            detail=i.display(),
        )
        for i in ml
    )


def compute_verdict(
    ref: TableRef,
    file: ChangedFile,
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> TableVerdict:
    suspects = _column_suspects(file)
    ml = find_ml_impacts(results, owners_by_urn, env_by_urn)
    if ml:
        affected = tuple(
            AffectedEntity(i.urn, i.name, i.kind, i.owner, f"downstream {i.kind}")
            for i in ml
        )
        # Pure ADDs with ML downstream are not silent breakage — LOW (green PR path).
        non_additive = any(c.kind != ChangeKind.ADD for c in file.columns)
        if non_additive:
            return TableVerdict(
                ref, file.file_path, file.columns, "CRITICAL", affected,
                _ml_message(file, ml, critical=True),
                why=_ml_why(ml, "ML_DOWNSTREAM"),
                column_suspects=suspects,
            )
        return TableVerdict(
            ref, file.file_path, file.columns, "LOW", affected,
            _ml_message(file, ml, critical=False),
            why=_ml_why(ml, "ML_DOWNSTREAM_ADDITIVE"),
            column_suspects=(),
        )

    dashboards = [r for r in results if r.platform.lower() in DASHBOARD_PLATFORMS]
    if dashboards:
        affected = tuple(
            AffectedEntity(r.urn, r.name, "DASHBOARD", None, "downstream BI consumer")
            for r in dashboards
        )
        why = tuple(
            WhyRule("DASHBOARD_DOWNSTREAM", r.urn, "DASHBOARD", r.hops, r.name)
            for r in dashboards
        )
        return TableVerdict(
            ref, file.file_path, file.columns, "HIGH", affected,
            "downstream dashboards/BI consumers", why=why, column_suspects=suspects,
        )
    if len(results) > 1:
        affected = tuple(
            AffectedEntity(r.urn, r.name, r.entity_type.upper() or "DATASET", None, "downstream")
            for r in results
        )
        why = tuple(
            WhyRule("MULTI_CONSUMER", r.urn, r.entity_type.upper() or "DATASET", r.hops, r.name)
            for r in results
        )
        return TableVerdict(
            ref, file.file_path, file.columns, "MEDIUM", affected,
            "multiple downstream consumers", why=why, column_suspects=suspects,
        )
    if all(c.kind == ChangeKind.ADD for c in file.columns):
        return TableVerdict(
            ref, file.file_path, file.columns, "LOW", (),
            "additive change only",
            why=(WhyRule("ADDITIVE_ONLY", ref.urn, "DATASET", 0, "no non-additive columns"),),
            column_suspects=(),
        )
    return TableVerdict(
        ref, file.file_path, file.columns, "MEDIUM", (),
        "non-additive change, no ML/dashboard consumers",
        why=(WhyRule("NON_ADDITIVE_NO_ML", ref.urn, "DATASET", 0, "no ML/dashboard path"),),
        column_suspects=suspects,
    )

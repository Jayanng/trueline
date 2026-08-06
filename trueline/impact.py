from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .config import TableRef
from .datahub_client import LineageResult
from .diff_parser import ChangedFile
from .ml_impact import find_ml_impacts


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Affected:
    urn: str
    name: str
    kind: str
    owner: str | None
    reason: str


@dataclass
class Verdict:
    ref: TableRef
    file_path: str
    severity: Severity
    columns: list  # ChangedColumn list
    affected: list[Affected]
    message: str = ""


def compute_verdict(
    ref: TableRef,
    file: ChangedFile,
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> Verdict:
    impacts = find_ml_impacts(results, owners_by_urn, env_by_urn)
    changed = [c for c in file.columns]

    affected: list[Affected] = []
    if changed and impacts:
        for imp in impacts:
            affected.append(Affected(
                urn=imp.urn,
                name=imp.name,
                kind=imp.kind,
                owner=imp.owner,
                reason=f"column(s) {','.join(c.name for c in changed)} affect {imp.kind} {imp.name}",
            ))

    if affected:
        has_owner = any(a.owner for a in affected)
        if has_owner:
            severity = Severity.CRITICAL
        else:
            severity = Severity.HIGH
        names = ", ".join(f"{a.name} ({a.kind})" for a in affected)
        cols = ", ".join(c.name for c in changed)
        msg = f"Changed columns [{cols}] impact {names}"
    elif changed:
        severity = Severity.LOW
        cols = ", ".join(c.name for c in changed)
        msg = f"No downstream ML entities found for columns [{cols}]"
    else:
        severity = Severity.LOW
        msg = "No SQL column changes detected"

    return Verdict(ref=ref, file_path=file.file_path, severity=severity, columns=changed, affected=affected, message=msg)
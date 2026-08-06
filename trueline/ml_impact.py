from __future__ import annotations

from dataclasses import dataclass

from .datahub_client import LineageResult

_ML_PREFIXES = {
    "urn:li:mlModel:": "MLMODEL",
    "urn:li:mlFeature:": "MLFEATURE",
    "urn:li:mlFeatureTable:": "MLFEATURETABLE",
    "urn:li:mlPrimaryKey:": "MLPRIMARYKEY",
    "urn:li:mlModelGroup:": "MLMODELGROUP",
    "urn:li:mlModelDeployment:": "MLMODELDEPLOYMENT",
}


def ml_kind(urn: str) -> str | None:
    for prefix, kind in _ML_PREFIXES.items():
        if urn.startswith(prefix):
            return kind
    return None


@dataclass(frozen=True)
class MLImpact:
    name: str
    urn: str
    kind: str
    env: str
    owner: str | None
    path: tuple[str, ...]
    hops: int = 1

    def display(self) -> str:
        parts = [f"{self.name} [{self.kind}]"]
        if self.env:
            parts.append(f"[{self.env}]")
        if self.owner:
            parts.append(f"owner: @{self.owner}")
        return " ".join(parts)


def find_ml_impacts(
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> list[MLImpact]:
    seen: dict[str, MLImpact] = {}
    for r in sorted(results, key=lambda x: -x.hops):
        kind = ml_kind(r.urn)
        if kind is None:
            continue
        if r.urn in seen:
            continue
        path = ()
        for p in (r.paths or ()):
            path = p
            break
        owners = owners_by_urn.get(r.urn, [])
        seen[r.urn] = MLImpact(
            name=r.name,
            urn=r.urn,
            kind=kind,
            env=env_by_urn.get(r.urn, ""),
            owner=owners[0] if owners else None,
            path=path,
            hops=int(r.hops or 1),
        )
    return list(seen.values())

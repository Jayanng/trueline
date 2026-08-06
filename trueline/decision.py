from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .contracts import ModelContract, matching_inputs
from .datahub_client import LineageResult
from .diff_parser import ChangeKind, ChangedColumn
from .warnings import CatalogWarning


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"
    QUARANTINE = "QUARANTINE"


DECISION_RANK = {
    Decision.ALLOW: 0,
    Decision.REVIEW: 1,
    Decision.BLOCK: 2,
    Decision.QUARANTINE: 3,
}


@dataclass(frozen=True)
class ContractEvaluation:
    contract_id: str
    column: str
    change_kind: ChangeKind
    policy: str
    outcome: str
    model_urn: str
    deployment_urn: str
    semantic: str
    reason: str


@dataclass(frozen=True)
class TableDecision:
    decision: Decision
    evaluations: tuple[ContractEvaluation, ...]
    reasons: tuple[str, ...]


def worst_decision(decisions: Iterable[Decision]) -> Decision:
    return max(decisions, key=lambda decision: DECISION_RANK[decision], default=Decision.ALLOW)


def evaluate_table(
    dataset_urn: str,
    changed_columns: tuple[ChangedColumn, ...],
    lineage: Iterable[LineageResult],
    warnings: Iterable[CatalogWarning],
    contracts: tuple[ModelContract, ...],
) -> TableDecision:
    lineage_urns = {result.urn for result in lineage}
    catalog_warnings = tuple(warnings)
    matches = matching_inputs(contracts, dataset_urn, changed_columns)
    evaluations: list[ContractEvaluation] = []
    decisions: list[Decision] = []
    reasons: list[str] = []

    matched_columns = {changed_column.name for _, _, changed_column in matches}
    if lineage_urns and any(
        column.name not in matched_columns and column.kind != ChangeKind.ADD
        for column in changed_columns
    ):
        decisions.append(Decision.REVIEW)
        reasons.append("Changed column has downstream lineage but no matching protected input")

    if not matches:
        return TableDecision(worst_decision(decisions), (), tuple(reasons))

    for contract, critical_input, changed_column in matches:
        warning_codes = {warning.code for warning in catalog_warnings}
        missing_evidence = []
        if contract.model_urn not in lineage_urns:
            missing_evidence.append(f"missing model evidence: {contract.model_urn}")
        if contract.deployment_urn not in lineage_urns:
            missing_evidence.append(
                f"missing deployment evidence: {contract.deployment_urn}"
            )
        catalog_evidence = sorted(
            warning_codes.intersection({"NO_DOWNSTREAM", "NO_ML_LINEAGE"})
        )
        if missing_evidence or catalog_evidence:
            outcome = "UNVERIFIED"
            decision = Decision.QUARANTINE
            details = missing_evidence + [
                f"catalog warning evidence: {code}" for code in catalog_evidence
            ]
            reason = (
                "Lineage evidence is incomplete for protected input: "
                + "; ".join(details)
            )
        elif critical_input.policy == "NO_DROP_OR_TYPE_CHANGE" and changed_column.kind in {
            ChangeKind.DROP,
            ChangeKind.TYPE_CHANGE,
        }:
            outcome = "VIOLATED"
            decision = Decision.BLOCK
            reason = f"{changed_column.kind.value} violates {critical_input.policy}"
        else:
            outcome = "SATISFIED"
            decision = Decision.ALLOW
            reason = f"{changed_column.kind.value} satisfies {critical_input.policy}"
        evaluations.append(ContractEvaluation(
            contract_id=contract.id,
            column=critical_input.column,
            change_kind=changed_column.kind,
            policy=critical_input.policy,
            outcome=outcome,
            model_urn=contract.model_urn,
            deployment_urn=contract.deployment_urn,
            semantic=critical_input.semantic,
            reason=reason,
        ))
        decisions.append(decision)
        reasons.append(reason)

    return TableDecision(worst_decision(decisions), tuple(evaluations), tuple(reasons))

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .diff_parser import ChangedColumn

SUPPORTED_POLICIES = frozenset({"NO_DROP_OR_TYPE_CHANGE"})


class ContractError(ValueError):
    pass


@dataclass(frozen=True)
class CriticalInput:
    dataset_urn: str
    column: str
    policy: str
    semantic: str


@dataclass(frozen=True)
class ModelContract:
    id: str
    model_urn: str
    deployment_urn: str
    critical_inputs: tuple[CriticalInput, ...]


def _required(obj: dict, key: str, where: str):
    value = obj.get(key)
    if value in (None, "", []):
        raise ContractError(f"missing {key} in {where}")
    return value


def load_contracts(path: Path) -> tuple[ModelContract, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load contract file {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("contracts"), list):
        raise ContractError("contract file must contain a contracts list")
    contracts: list[ModelContract] = []
    for index, raw in enumerate(payload["contracts"]):
        if not isinstance(raw, dict):
            raise ContractError(f"contract[{index}] must be an object")
        inputs_raw = _required(raw, "critical_inputs", f"contract[{index}]")
        if not isinstance(inputs_raw, list):
            raise ContractError(f"contract[{index}].critical_inputs must be a list")
        inputs: list[CriticalInput] = []
        for input_index, item in enumerate(inputs_raw):
            if not isinstance(item, dict):
                raise ContractError(f"contract[{index}].critical_inputs[{input_index}] must be an object")
            policy = _required(item, "policy", f"contract[{index}].critical_inputs[{input_index}]")
            if policy not in SUPPORTED_POLICIES:
                raise ContractError(f"unsupported policy: {policy}")
            inputs.append(CriticalInput(
                dataset_urn=str(_required(item, "dataset_urn", "critical input")),
                column=str(_required(item, "column", "critical input")),
                policy=str(policy),
                semantic=str(item.get("semantic", "")),
            ))
        contracts.append(ModelContract(
            id=str(_required(raw, "id", f"contract[{index}]")),
            model_urn=str(_required(raw, "model_urn", f"contract[{index}]")),
            deployment_urn=str(_required(raw, "deployment_urn", f"contract[{index}]")),
            critical_inputs=tuple(inputs),
        ))
    return tuple(contracts)


def matching_inputs(
    contracts: tuple[ModelContract, ...],
    dataset_urn: str,
    changed_columns: tuple[ChangedColumn, ...],
) -> tuple[tuple[ModelContract, CriticalInput, ChangedColumn], ...]:
    changed = {column.name: column for column in changed_columns}
    return tuple(
        (contract, critical_input, changed[critical_input.column])
        for contract in contracts
        for critical_input in contract.critical_inputs
        if critical_input.dataset_urn == dataset_urn
        and critical_input.column in changed
    )

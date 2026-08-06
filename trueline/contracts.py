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


def _required_string(obj: dict, key: str, where: str) -> str:
    value = _required(obj, key, where)
    if not isinstance(value, str):
        raise ContractError(f"{key} in {where} must be a string")
    return value


def _reject_unknown(obj: dict, allowed: frozenset[str], where: str) -> None:
    unknown = set(obj) - allowed
    if unknown:
        raise ContractError(f"unknown fields in {where}: {', '.join(sorted(unknown))}")


def load_contracts(path: Path) -> tuple[ModelContract, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load contract file {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("contracts"), list):
        raise ContractError("contract file must contain a contracts list")
    _reject_unknown(payload, frozenset({"contracts"}), "contract file")
    contracts: list[ModelContract] = []
    for index, raw in enumerate(payload["contracts"]):
        if not isinstance(raw, dict):
            raise ContractError(f"contract[{index}] must be an object")
        where = f"contract[{index}]"
        _reject_unknown(
            raw,
            frozenset({"id", "model_urn", "deployment_urn", "critical_inputs"}),
            where,
        )
        inputs_raw = _required(raw, "critical_inputs", where)
        if not isinstance(inputs_raw, list):
            raise ContractError(f"contract[{index}].critical_inputs must be a list")
        inputs: list[CriticalInput] = []
        for input_index, item in enumerate(inputs_raw):
            if not isinstance(item, dict):
                raise ContractError(f"contract[{index}].critical_inputs[{input_index}] must be an object")
            input_where = f"contract[{index}].critical_inputs[{input_index}]"
            _reject_unknown(
                item,
                frozenset({"dataset_urn", "column", "policy", "semantic"}),
                input_where,
            )
            policy = _required_string(item, "policy", input_where)
            if policy not in SUPPORTED_POLICIES:
                raise ContractError(f"unsupported policy: {policy}")
            semantic = item.get("semantic", "")
            if not isinstance(semantic, str):
                raise ContractError(f"semantic in {input_where} must be a string")
            inputs.append(CriticalInput(
                dataset_urn=_required_string(item, "dataset_urn", input_where),
                column=_required_string(item, "column", input_where),
                policy=policy,
                semantic=semantic,
            ))
        contracts.append(ModelContract(
            id=_required_string(raw, "id", where),
            model_urn=_required_string(raw, "model_urn", where),
            deployment_urn=_required_string(raw, "deployment_urn", where),
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

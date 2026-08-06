import json

import pytest

from trueline.contracts import ContractError, load_contracts, matching_inputs
from trueline.diff_parser import ChangeKind, ChangedColumn


DATASET = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.patient_labs,PROD)"
MODEL = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)"
DEPLOYMENT = (
    "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)"
)


def _payload():
    return {
        "contracts": [{
            "id": "sepsis-risk-v3-prod",
            "model_urn": MODEL,
            "deployment_urn": DEPLOYMENT,
            "critical_inputs": [{
                "dataset_urn": DATASET,
                "column": "lactate_mmol_l",
                "policy": "NO_DROP_OR_TYPE_CHANGE",
                "semantic": "blood lactate in mmol/L",
            }],
        }]
    }


def test_load_contracts_parses_valid_file(tmp_path):
    path = tmp_path / "contracts.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")

    contracts = load_contracts(path)

    assert contracts[0].id == "sepsis-risk-v3-prod"
    assert contracts[0].critical_inputs[0].column == "lactate_mmol_l"
    assert contracts[0].critical_inputs[0].policy == "NO_DROP_OR_TYPE_CHANGE"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.pop("contracts"),
        lambda p: p["contracts"][0].pop("deployment_urn"),
        lambda p: p["contracts"][0]["critical_inputs"][0].update({"policy": "UNKNOWN"}),
        lambda p: p["contracts"][0].update({"critical_inputs": []}),
    ],
)
def test_load_contracts_rejects_malformed_contract(tmp_path, mutation):
    payload = _payload()
    mutation(payload)
    path = tmp_path / "contracts.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ContractError):
        load_contracts(path)


def test_matching_inputs_requires_exact_dataset_and_column(tmp_path):
    path = tmp_path / "contracts.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    contracts = load_contracts(path)
    changed = (
        ChangedColumn("lactate_mmol_l", ChangeKind.DROP),
        ChangedColumn("notes", ChangeKind.ADD),
    )

    matches = matching_inputs(contracts, DATASET, changed)

    assert len(matches) == 1
    assert matches[0][0].id == "sepsis-risk-v3-prod"
    assert matches[0][1].column == "lactate_mmol_l"
    assert matches[0][2].kind == ChangeKind.DROP
    assert matching_inputs(contracts, DATASET.lower(), changed) == ()

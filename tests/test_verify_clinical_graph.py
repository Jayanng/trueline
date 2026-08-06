from dataclasses import replace

import pytest

from seed import verify_clinical_graph
from tests.fakes import (
    CLINICAL_DEPLOY_URN,
    CLINICAL_FEATURE_URN,
    CLINICAL_MODEL_URN,
    LINEAGE,
    PATIENT_LABS,
    SEPSIS_FEATURES,
)


class BrokenPathGateway:
    def __init__(self, _cfg):
        self.results = list(LINEAGE[PATIENT_LABS.urn])
        deployment = self.results[-1]
        self.results[-1] = replace(
            deployment,
            paths=((
                PATIENT_LABS.urn,
                SEPSIS_FEATURES.urn,
                CLINICAL_MODEL_URN,
                CLINICAL_FEATURE_URN,
                CLINICAL_DEPLOY_URN,
            ),),
        )

    def downstream(self, _ref, max_hops=4):
        return self.results

    def owners(self, _urn):
        return ["clinical-ml-oncall"]

    def environment(self, _urn):
        return "PROD"

    def search(self, query, entity_type="", limit=20):
        return {
            "sepsis_risk_v3": [CLINICAL_MODEL_URN],
            "icu-early-warning": [CLINICAL_DEPLOY_URN],
        }[query]


def test_verifier_rejects_present_entities_without_exact_connected_path(monkeypatch, capsys):
    monkeypatch.setattr(verify_clinical_graph, "DataHubGateway", BrokenPathGateway)

    with pytest.raises(SystemExit) as exc:
        verify_clinical_graph.main()

    assert exc.value.code == 1
    assert "FAIL: exact clinical deployment path is missing" in capsys.readouterr().out

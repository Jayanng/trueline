import pytest

from trueline.config import TableRef
from tests.fakes import (
    CLINICAL_DEPLOY_URN,
    CLINICAL_MODEL_URN,
    CUSTOMERS,
    FakeGateway,
    LINEAGE,
    PATIENT_LABS,
    TERMS,
)

UP = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
DOWN = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="FEATURE_ORDER_RISK")


@pytest.fixture
def gateway():
    return FakeGateway(seed=LINEAGE, terms=TERMS)


def test_downstream_returns_results(gateway: FakeGateway):
    results = gateway.downstream(UP, max_hops=4)
    assert any(r.urn == "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)" for r in results)


def test_downstream_column_filter(gateway: FakeGateway):
    assert gateway.downstream(UP, column="return_date", max_hops=1) == []


def test_owners_and_environment(gateway: FakeGateway):
    model = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)"
    assert gateway.owners(model) == ["datahub"]
    assert gateway.environment(model) == "PROD"
    # Env falls back from the trailing PROD segment on ML/dataset URNs
    assert gateway.environment("urn:li:dataset:(urn:li:dataPlatform:looker,foo,PROD)") == "PROD"
    assert gateway.environment("urn:li:mlFeature:(order_entry,feature_order_risk)") == ""


def test_downstream_includes_deployment(gateway: FakeGateway):
    results = gateway.downstream(UP, max_hops=4)
    assert any(r.urn.endswith("fraud-scoring-endpoint,PROD)") for r in results)


def test_patient_labs_path_reaches_owned_prod_sepsis_model_and_deployment(gateway: FakeGateway):
    results = gateway.downstream(PATIENT_LABS, max_hops=4)
    clinical_entities = {
        result.urn
        for result in results
        if result.entity_type in {"mlmodel", "mlmodeldeployment"}
    }
    deployment = next(result for result in results if result.urn == CLINICAL_DEPLOY_URN)

    assert clinical_entities == {CLINICAL_MODEL_URN, CLINICAL_DEPLOY_URN}
    assert deployment.paths == ((
        PATIENT_LABS.urn,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.sepsis_features,PROD)",
        "urn:li:mlFeature:(clinical,lactate_trend)",
        CLINICAL_MODEL_URN,
        CLINICAL_DEPLOY_URN,
    ),)
    assert gateway.owners(CLINICAL_MODEL_URN) == ["clinical-ml-oncall"]
    assert gateway.environment(CLINICAL_MODEL_URN) == "PROD"
    assert gateway.environment(CLINICAL_DEPLOY_URN) == "PROD"


def test_column_terms(gateway: FakeGateway):
    assert any("pii" in t.lower() for t in gateway.column_terms(CUSTOMERS, "cust_email"))


def test_add_lineage_records(gateway: FakeGateway):
    gateway.add_lineage(UP, DOWN, column_lineage={"risk_score": ["return_date"]}, wait=True)
    assert ("LINEAGE", UP.urn, DOWN.urn, {"risk_score": ["return_date"]}) in gateway.writes


@pytest.mark.parametrize(
    "mapping",
    [None, {}, {"risk_score": []}, {"risk_score": ["", "   "]}],
)
def test_datahub_add_lineage_refuses_unusable_mapping_before_sdk_call(mapping):
    from types import SimpleNamespace

    from trueline.datahub_client import DataHubGateway

    class LineageSDK:
        def add_lineage(self, **kwargs):
            raise AssertionError("SDK must not be called for unusable mappings")

    gateway = DataHubGateway.__new__(DataHubGateway)
    gateway._client = SimpleNamespace(lineage=LineageSDK())

    with pytest.raises(ValueError, match="refusing add_lineage"):
        gateway.add_lineage(UP, DOWN, column_lineage=mapping)


def test_add_term_records(gateway: FakeGateway):
    gateway.add_term(DOWN, "customer_email", "urn:li:glossaryTerm:pii.email")
    assert ("TERM", DOWN.urn, "customer_email", "urn:li:glossaryTerm:pii.email") in gateway.writes

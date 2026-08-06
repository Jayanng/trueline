import pytest

from trueline.config import TableRef
from tests.fakes import CUSTOMERS, FakeGateway, LINEAGE, TERMS

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
    assert gateway.owners(model) == ["riya"]
    assert gateway.environment(model) == "PROD"
    assert gateway.environment("urn:li:dataset:(urn:li:dataPlatform:looker,foo,PROD)") == ""


def test_column_terms(gateway: FakeGateway):
    assert any("pii" in t.lower() for t in gateway.column_terms(CUSTOMERS, "cust_email"))


def test_add_lineage_records(gateway: FakeGateway):
    gateway.add_lineage(UP, DOWN, column_lineage={"risk_score": ["return_date"]}, wait=True)
    assert ("LINEAGE", UP.urn, DOWN.urn, {"risk_score": ["return_date"]}) in gateway.writes


def test_add_term_records(gateway: FakeGateway):
    gateway.add_term(DOWN, "customer_email", "urn:li:glossaryTerm:pii.email")
    assert ("TERM", DOWN.urn, "customer_email", "urn:li:glossaryTerm:pii.email") in gateway.writes
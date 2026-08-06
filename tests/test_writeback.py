import asyncio
from pathlib import Path

from trueline.config import TableRef
from trueline.diff_parser import ChangedFile
from trueline.state import StateStore
from trueline.writeback import (apply_proposals, derive_column_mapping,
                                normalize_jinja, plan_term_drift, plan_writebacks)
from tests.fakes import CUSTOMERS, FakeGateway, FEATURE, LINEAGE, ORDER_ITEMS, TERMS

FIXTURES = Path(__file__).parent / "fixtures"
FEATURE_SQL = (FIXTURES / "feature_order_risk_new.sql").read_text(encoding="utf-8")

FILE = ChangedFile(file_path="demo_repo/models/feature_order_risk.sql", columns=(), is_sql=True)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_normalize_jinja():
    assert normalize_jinja("from {{ ref('order_items') }}") == "from order_items"
    assert "{{" not in normalize_jinja("select * from {{ this }}")


def test_derive_column_mapping():
    mapping = derive_column_mapping(FEATURE_SQL, ORDER_ITEMS)
    assert mapping["risk_score"] == ["order_total"]
    assert mapping["order_id"] == ["order_id"]
    assert "customer_email" not in mapping
    cust_mapping = derive_column_mapping(FEATURE_SQL, CUSTOMERS)
    assert cust_mapping["customer_email"] == ["cust_email"]


def test_plan_writebacks_finds_gap():
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    proposals = run(plan_writebacks(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    assert any(p.kind == "LINEAGE" and "risk_score" in p.detail["mapping"] for p in proposals)
    assert all(p.target_urn == FEATURE.urn for p in proposals)


def test_plan_term_drift_propagates_pii():
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    proposals = run(plan_term_drift(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    pii = [p for p in proposals if p.kind == "GLOSSARY_TERM"]
    assert pii, "expected a PII propagation proposal"
    assert pii[0].detail["column"] == "customer_email"


def test_apply_proposals_commits_and_idempotent(tmp_path):
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    state = StateStore(tmp_path / "state.db")
    run(state.init())
    proposals = run(plan_writebacks(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    first = run(apply_proposals(proposals, gateway, state, "run-1"))
    second = run(apply_proposals(proposals, gateway, state, "run-2"))
    assert all(status == "COMMITTED" for _, status, _ in first)
    assert all(status == "SKIPPED" for _, status, _ in second)
    assert any(w[0] == "LINEAGE" for w in gateway.writes)


def test_apply_refuses_empty_lineage_mapping(tmp_path):
    from trueline.writeback import Proposal

    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    state = StateStore(tmp_path / "state.db")
    run(state.init())
    proposals = [
        Proposal(
            kind="LINEAGE",
            target_urn=FEATURE.urn,
            detail={"upstream": ORDER_ITEMS.urn, "mapping": mapping},
            source="test",
        )
        for mapping in (None, {}, {"x": []}, {"x": ["", "   "]})
    ]
    out = run(apply_proposals(proposals, gateway, state, "run-empty"))
    assert all(status == "BLOCKED_EMPTY" for _, status, _ in out)
    assert all(warn is not None and warn.code == "EMPTY_LINEAGE_REFUSED" for _, _, warn in out)
    assert not any(w[0] == "LINEAGE" for w in gateway.writes)


def test_fake_gateway_add_lineage_rejects_empty():
    gateway = FakeGateway()
    import pytest

    with pytest.raises(ValueError, match="empty column_lineage"):
        gateway.add_lineage(ORDER_ITEMS, FEATURE, column_lineage={})


def test_fake_gateway_add_lineage_rejects_missing_column_mapping():
    gateway = FakeGateway()
    import pytest

    with pytest.raises(ValueError, match="column mapping is required"):
        gateway.add_lineage(ORDER_ITEMS, FEATURE, column_lineage=None)

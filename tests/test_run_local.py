import argparse
import json
from types import SimpleNamespace

import pytest

from scripts import run_local
from scripts.run_local import _decision_exit, _verdict_to_dict, _worst_severity
from tests.fakes import FakeGateway, ORDER_ITEMS
from trueline.decision import Decision, TableDecision
from trueline.diff_parser import ChangeKind, ChangedColumn
from trueline.impact import TableVerdict


def test_decision_exit_codes():
    assert _decision_exit(Decision.ALLOW, shadow=False) == 0
    assert _decision_exit(Decision.REVIEW, shadow=False) == 0
    assert _decision_exit(Decision.BLOCK, shadow=False) == 1
    assert _decision_exit(Decision.QUARANTINE, shadow=False) == 1
    assert _decision_exit(Decision.BLOCK, shadow=True) == 0


def test_worst_severity_does_not_use_lexical_order():
    assert _worst_severity(["LOW", "CRITICAL", "MEDIUM"]) == "CRITICAL"


def test_verdict_serialization_includes_contract_decision():
    verdict = TableVerdict(
        ref=ORDER_ITEMS,
        file_path="models/order_items.sql",
        columns=(ChangedColumn("status", ChangeKind.ADD),),
        severity="LOW",
        affected=(),
        message="additive change only",
    )
    table_decision = TableDecision(Decision.ALLOW, (), ())

    payload = _verdict_to_dict(verdict, table_decision)

    assert payload["decision"] == "ALLOW"
    assert payload["contract_evaluations"] == []


@pytest.mark.asyncio
async def test_no_sql_changes_return_without_constructing_gateway(tmp_path, monkeypatch):
    table_map = tmp_path / "table_map.json"
    table_map.write_text("{}", encoding="utf-8")
    contracts = tmp_path / "contracts.json"
    contracts.write_text('{"contracts": []}', encoding="utf-8")
    monkeypatch.setattr(run_local, "git_diff", lambda *args: "")
    monkeypatch.setattr(
        run_local,
        "Config",
        lambda: SimpleNamespace(dry_run=True, state_db=tmp_path / "state.db"),
    )

    def fail_if_constructed(_cfg):
        raise AssertionError("empty diffs must not require a DataHub gateway")

    monkeypatch.setattr(run_local, "DataHubGateway", fail_if_constructed)
    args = argparse.Namespace(
        repo=tmp_path,
        base="main",
        head="feature",
        pr="123",
        author=None,
        table_map=table_map,
        contracts=contracts,
        commit=False,
        verify=False,
        shadow=False,
        json=None,
        comment_out=None,
        notify_out=None,
    )

    assert await run_local.run(args) == 0


@pytest.mark.asyncio
async def test_dry_run_does_not_stamp_reviewed(tmp_path, monkeypatch):
    table_map = tmp_path / "table_map.json"
    table_map.write_text(
        json.dumps({
            "models/order_items.sql": {
                "platform": ORDER_ITEMS.platform,
                "db": ORDER_ITEMS.db,
                "schema": ORDER_ITEMS.schema,
                "table": ORDER_ITEMS.table,
            }
        }),
        encoding="utf-8",
    )
    contracts = tmp_path / "contracts.json"
    contracts.write_text('{"contracts": []}', encoding="utf-8")
    gateway = FakeGateway(seed={})
    diff = """diff --git a/models/order_items.sql b/models/order_items.sql
index 1111111..2222222 100644
--- a/models/order_items.sql
+++ b/models/order_items.sql
@@ -1 +1,2 @@
 SELECT id
+     , status
 FROM order_items
"""

    monkeypatch.setattr(run_local, "git_diff", lambda *args: diff)
    monkeypatch.setattr(
        run_local,
        "git_show",
        lambda *args: "SELECT id, status FROM order_items",
    )
    monkeypatch.setattr(
        run_local,
        "Config",
        lambda: SimpleNamespace(
            dry_run=True,
            state_db=tmp_path / "state.db",
            has_llm=False,
            gms_url="http://datahub.invalid",
            gms_token="",
            mcp_url="http://mcp.invalid",
        ),
    )
    monkeypatch.setattr(run_local, "DataHubGateway", lambda cfg: gateway)
    args = argparse.Namespace(
        repo=tmp_path,
        base="main",
        head="feature",
        pr="123",
        author=None,
        table_map=table_map,
        contracts=contracts,
        commit=False,
        verify=False,
        shadow=False,
        json=None,
        comment_out=None,
        notify_out=None,
    )

    assert await run_local.run(args) == 0
    assert not any(write[0] == "REVIEWED" for write in gateway.writes)

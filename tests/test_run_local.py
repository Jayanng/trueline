import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from scripts import run_local
from scripts.run_local import _decision_exit, _verdict_to_dict, _worst_severity
from tests.fakes import FakeGateway, ORDER_ITEMS
from trueline.config import TableRef
from trueline.datahub_client import LineageResult
from trueline.decision import ContractEvaluation, Decision, TableDecision
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


def test_verdict_serialization_preserves_missing_deployment_evidence():
    deployment = "urn:li:mlModelDeployment:missing-clinical-deployment"
    verdict = TableVerdict(
        ref=ORDER_ITEMS,
        file_path="models/order_items.sql",
        columns=(ChangedColumn("lactate_mmol_l", ChangeKind.DROP),),
        severity="CRITICAL",
        affected=(),
        message="protected input evidence is incomplete",
    )
    reason = f"Missing deployment evidence: {deployment}"
    evaluation = ContractEvaluation(
        contract_id="sepsis-risk-v3-prod",
        column="lactate_mmol_l",
        change_kind=ChangeKind.DROP,
        policy="NO_DROP_OR_TYPE_CHANGE",
        outcome="UNVERIFIED",
        model_urn="urn:li:mlModel:sepsis-risk-v3",
        deployment_urn=deployment,
        semantic="blood lactate in mmol/L",
        reason=reason,
    )
    table_decision = TableDecision(Decision.QUARANTINE, (evaluation,), (reason,))

    payload = _verdict_to_dict(verdict, table_decision)

    assert payload["decision"] == "QUARANTINE"
    serialized = payload["contract_evaluations"][0]
    assert serialized["reason"] == reason
    assert deployment in serialized["reason"]


def _blocking_contract_run(tmp_path, monkeypatch, *, shadow=False):
    ref = TableRef("snowflake", "clinical", "", "patient_labs")
    model_urn = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)"
    deployment_urn = (
        "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)"
    )
    table_map = tmp_path / "table_map.json"
    table_map.write_text(
        json.dumps({
            "models/patient_labs.sql": {
                "platform": ref.platform,
                "db": ref.db,
                "schema": ref.schema,
                "table": ref.table,
            }
        }),
        encoding="utf-8",
    )
    contracts = tmp_path / "contracts.json"
    contracts.write_text(
        json.dumps({
            "contracts": [{
                "id": "sepsis-risk-v3-prod",
                "model_urn": model_urn,
                "deployment_urn": deployment_urn,
                "critical_inputs": [{
                    "dataset_urn": ref.urn,
                    "column": "lactate_mmol_l",
                    "policy": "NO_DROP_OR_TYPE_CHANGE",
                    "semantic": "blood lactate in mmol/L",
                }],
            }]
        }),
        encoding="utf-8",
    )
    gateway = FakeGateway(seed={
        ref.urn: [
            LineageResult(model_urn, "mlmodel", "mlflow", "sepsis_risk_v3", 1),
            LineageResult(
                deployment_urn,
                "mlmodeldeployment",
                "mlflow",
                "icu-early-warning",
                2,
            ),
        ]
    })
    diff = """diff --git a/models/patient_labs.sql b/models/patient_labs.sql
index 1111111..2222222 100644
--- a/models/patient_labs.sql
+++ b/models/patient_labs.sql
@@ -1,3 +1,2 @@
 SELECT id
-lactate_mmol_l
 FROM patient_labs
"""
    monkeypatch.setattr(run_local, "git_diff", lambda *args: diff)
    monkeypatch.setattr(
        run_local,
        "git_show",
        lambda *args: "SELECT id FROM patient_labs",
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
    return argparse.Namespace(
        repo=tmp_path,
        base="main",
        head="feature",
        pr="123",
        author=None,
        table_map=table_map,
        contracts=contracts,
        commit=False,
        verify=False,
        shadow=shadow,
        json=tmp_path / "result.json",
        comment_out=tmp_path / "comment.md",
        notify_out=tmp_path / "notify.json",
    )


@pytest.mark.asyncio
async def test_matching_contract_blocks_and_writes_decision_evidence(tmp_path, monkeypatch):
    args = _blocking_contract_run(tmp_path, monkeypatch)

    assert await run_local.run(args) == 1

    payload = json.loads(args.json.read_text(encoding="utf-8"))
    assert payload["decision"] == "BLOCK"
    assert payload["notify"]["decision"] == "BLOCK"
    assert payload["notify"]["severity"] == "CRITICAL"
    assert payload["notify"]["text"] == "Trueline CRITICAL on PR #123"
    assert payload["tables"][0]["decision"] == "BLOCK"
    assert payload["tables"][0]["contract_evaluations"][0] == {
        "contract_id": "sepsis-risk-v3-prod",
        "column": "lactate_mmol_l",
        "change_kind": "DROP",
        "policy": "NO_DROP_OR_TYPE_CHANGE",
        "outcome": "VIOLATED",
        "model_urn": "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)",
        "deployment_urn": "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)",
        "semantic": "blood lactate in mmol/L",
        "reason": "DROP violates NO_DROP_OR_TYPE_CHANGE",
    }
    comment = args.comment_out.read_text(encoding="utf-8")
    assert "Overall: `BLOCK`" in comment
    assert "`patient_labs`: `BLOCK`" in comment
    assert "`sepsis-risk-v3-prod`" in comment


@pytest.mark.asyncio
async def test_shadow_writes_requested_outputs_before_returning_zero(tmp_path, monkeypatch):
    args = _blocking_contract_run(tmp_path, monkeypatch, shadow=True)

    assert await run_local.run(args) == 0

    payload = json.loads(args.json.read_text(encoding="utf-8"))
    assert payload["decision"] == "BLOCK"
    assert payload["shadow"] is True
    assert "Overall: `BLOCK`" in args.comment_out.read_text(encoding="utf-8")
    notify = json.loads(args.notify_out.read_text(encoding="utf-8"))
    assert notify["decision"] == "BLOCK"
    assert notify["severity"] == "CRITICAL"
    assert notify["text"] == "Trueline CRITICAL on PR #123"


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


def test_cli_help_is_ascii_and_cp1252_safe():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    proc = subprocess.run(
        [sys.executable, "scripts/run_local.py", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    proc.stdout.encode("ascii")

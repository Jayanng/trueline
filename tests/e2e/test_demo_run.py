import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_local.py"
CONTRACTS = ROOT / "contracts" / "model-change-contracts.json"


def _run_clinical_branch(tmp_path, head, *, contracts=CONTRACTS):
    out_json = tmp_path / f"{head.rsplit('/', 1)[-1]}.json"
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(ROOT),
            "--base",
            "main",
            "--head",
            head,
            "--pr",
            "clinical-demo",
            "--contracts",
            str(contracts),
            "--json",
            str(out_json),
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ),
    )
    assert out_json.is_file(), out.stdout + out.stderr
    return out, json.loads(out_json.read_text(encoding="utf-8"))


def test_demo_pr_is_critical_dry_run(e2e_enabled):
    env = dict(os.environ)
    out_json = ROOT / ".trueline" / "e2e.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(ROOT),
            "--base",
            "main",
            "--head",
            "demo/pr-2847",
            "--pr",
            "2847",
            "--author",
            "maya",
            "--json",
            str(out_json),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["verdict"] == "CRITICAL"
    assert any("fraud_model_v4" in str(t["affected"]) for t in payload["tables"])
    assert payload["dry_run"] is True
    assert "nothing was written" in out.stdout.lower() or "dry-run" in out.stdout.lower()


def test_demo_pr_commit_then_verify(e2e_enabled):
    env = dict(os.environ)
    env["TRUELINE_DRY_RUN"] = "false"  # --commit only applies when dry-run is off
    out = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(ROOT),
            "--base",
            "main",
            "--head",
            "demo/pr-2847",
            "--pr",
            "2847",
            "--commit",
            "--verify",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    assert "COMMITTED" in out.stdout
    assert "VERIFIED" in out.stdout
    # second run is idempotent
    out2 = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(ROOT),
            "--base",
            "main",
            "--head",
            "demo/pr-2847",
            "--pr",
            "2847",
            "--commit",
            "--verify",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert "SKIPPED" in out2.stdout


def test_unsafe_clinical_branch_blocks_with_contract_evidence(e2e_enabled, tmp_path):
    out, payload = _run_clinical_branch(tmp_path, "demo/sepsis-unsafe")

    assert out.returncode == 1, out.stdout + out.stderr
    assert payload["decision"] == "BLOCK"
    evaluations = payload["tables"][0]["contract_evaluations"]
    assert evaluations[0]["contract_id"] == "sepsis-risk-v3-prod"
    assert evaluations[0]["model_urn"]
    assert evaluations[0]["deployment_urn"]


def test_safe_clinical_branch_allows_additive_change(e2e_enabled, tmp_path):
    out, payload = _run_clinical_branch(tmp_path, "demo/sepsis-safe")

    assert out.returncode == 0, out.stdout + out.stderr
    assert payload["decision"] == "ALLOW"


def test_missing_deployment_evidence_quarantines(e2e_enabled, tmp_path):
    contracts = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    missing_deployment = (
        "urn:li:mlModelDeployment:"
        "(urn:li:dataPlatform:mlflow,intentionally-absent,PROD)"
    )
    contracts["contracts"][0]["deployment_urn"] = missing_deployment
    temporary_contracts = tmp_path / "contracts.json"
    temporary_contracts.write_text(json.dumps(contracts), encoding="utf-8")

    out, payload = _run_clinical_branch(
        tmp_path,
        "demo/sepsis-unsafe",
        contracts=temporary_contracts,
    )

    assert out.returncode == 1, out.stdout + out.stderr
    assert payload["decision"] == "QUARANTINE"
    evaluations = payload["tables"][0]["contract_evaluations"]
    assert evaluations[0]["deployment_urn"] == missing_deployment
    assert "unverified" in evaluations[0]["reason"].lower()

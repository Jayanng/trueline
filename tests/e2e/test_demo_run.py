import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_local.py"


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

import shutil
import subprocess
from pathlib import Path

import pytest

from trueline.comment import render_decision
from trueline.decision import ContractEvaluation, Decision, TableDecision
from trueline.diff_parser import ChangeKind


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "setup_clinical_demo_branches.ps1"
FIXTURES = ROOT / "tests" / "fixtures"


def _git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _make_demo_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "tests" / "fixtures").mkdir(parents=True)
    (repo / "demo_repo" / "models").mkdir(parents=True)
    shutil.copy2(SCRIPT, repo / "scripts" / SCRIPT.name)
    shutil.copy2(FIXTURES / "patient_labs_unsafe.sql", repo / "tests" / "fixtures")
    shutil.copy2(FIXTURES / "patient_labs_safe.sql", repo / "tests" / "fixtures")
    model = repo / "demo_repo" / "models" / "patient_labs.sql"
    model.write_text(
        "select patient_id, observed_at, lactate_mmol_l from raw_patient_labs\n",
        encoding="utf-8",
    )
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Task 6 Test")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    return repo


def _run_setup(repo, *args):
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo / "scripts" / SCRIPT.name),
            *args,
        ],
        capture_output=True,
        text=True,
    )


def _create_original_target_branches(repo):
    model = repo / "demo_repo" / "models" / "patient_labs.sql"
    originals = {}
    for branch, marker in (
        ("demo/sepsis-unsafe", "original unsafe branch"),
        ("demo/sepsis-safe", "original safe branch"),
    ):
        _git(repo, "switch", "--create", branch, "main")
        model.write_text(f"select '{marker}' as marker\n", encoding="utf-8")
        _git(repo, "add", "demo_repo/models/patient_labs.sql")
        _git(repo, "commit", "-m", marker)
        originals[branch] = _git(repo, "rev-parse", branch).stdout.strip()
        _git(repo, "switch", "main")
    return originals


@pytest.mark.parametrize("starting_branch", ["demo/sepsis-unsafe", "demo/sepsis-safe"])
@pytest.mark.skipif(
    shutil.which("powershell.exe") is None,
    reason="Windows PowerShell is unavailable",
)
def test_force_setup_from_target_branch_restores_starting_branch_and_recreates_refs(
    tmp_path,
    starting_branch,
):
    repo = _make_demo_repo(tmp_path)
    _git(repo, "branch", starting_branch)
    _git(repo, "switch", starting_branch)

    result = _run_setup(repo, "-Base", "main", "-Force")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(repo, "branch", "--show-current").stdout.strip() == starting_branch
    for branch, message, fixture in (
        ("demo/sepsis-unsafe", "demo: unsafe sepsis input change", "patient_labs_unsafe.sql"),
        ("demo/sepsis-safe", "demo: safe additive clinical change", "patient_labs_safe.sql"),
    ):
        commit = _git(repo, "log", "-1", "--format=%s", branch).stdout.strip()
        assert commit == message
        branch_model = _git(
            repo,
            "show",
            f"{branch}:demo_repo/models/patient_labs.sql",
        ).stdout
        assert branch_model == (FIXTURES / fixture).read_text(encoding="utf-8")


def test_rendered_quarantine_reason_names_missing_deployment_urn():
    deployment = "urn:li:mlModelDeployment:missing-clinical-deployment"
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

    rendered = render_decision(
        Decision.QUARANTINE,
        [TableDecision(Decision.QUARANTINE, (evaluation,), (reason,))],
    )

    assert reason in rendered


@pytest.mark.parametrize("starting_branch", ["demo/sepsis-unsafe", "demo/sepsis-safe"])
@pytest.mark.parametrize("failure_point", ["after_stage", "after_commit"])
@pytest.mark.skipif(
    shutil.which("powershell.exe") is None,
    reason="Windows PowerShell is unavailable",
)
def test_force_failure_restores_original_target_refs_and_starting_branch(
    tmp_path,
    starting_branch,
    failure_point,
):
    repo = _make_demo_repo(tmp_path)
    script = repo / "scripts" / SCRIPT.name
    needle = {
        "after_stage": "Invoke-Git add -- $modelPath",
        "after_commit": "Invoke-Git commit -m $branch.Message",
    }[failure_point]
    script.write_text(
        script.read_text(encoding="utf-8").replace(
            needle,
            f'{needle}\n        throw "intentional {failure_point} failure"',
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "scripts/setup_clinical_demo_branches.ps1")
    _git(repo, "commit", "-m", "inject setup failure")
    originals = _create_original_target_branches(repo)
    _git(repo, "switch", starting_branch)

    result = _run_setup(repo, "-Base", "main", "-Force")

    assert result.returncode != 0
    assert _git(repo, "branch", "--show-current").stdout.strip() == starting_branch
    assert _git(repo, "status", "--porcelain").stdout == ""
    for branch, original_sha in originals.items():
        assert _git(repo, "rev-parse", branch).stdout.strip() == original_sha

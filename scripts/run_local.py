#!/usr/bin/env python
"""Trueline guard pipeline for local/CI diffs (primary demo path).

Usage examples:
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847 --commit --verify
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847 --shadow

Workflow (do not skip steps — empty lineage is not "safe"):
  1) seed/seed_ml_tail.py  2) seed/verify_graph.py  3) MCP up
  4) run_local against git base...head (SQL read from head via git show)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trueline.agent import Agent  # noqa: E402
from trueline.comment import build_notify_payload, render_comment  # noqa: E402
from trueline.config import Config, load_table_map  # noqa: E402
from trueline.contracts import load_contracts  # noqa: E402
from trueline.datahub_client import DataHubGateway  # noqa: E402
from trueline.decision import Decision, TableDecision, evaluate_table, worst_decision  # noqa: E402
from trueline.diff_parser import parse_diff  # noqa: E402
from trueline.impact import compute_verdict  # noqa: E402
from trueline.ml_impact import find_ml_impacts  # noqa: E402
from trueline.state import StateStore  # noqa: E402
from trueline.warnings import (  # noqa: E402
    CatalogWarning,
    no_downstream_at_all,
    no_ml_lineage,
    unmapped_sql_file,
)
from trueline.writeback import apply_proposals, plan_term_drift, plan_writebacks  # noqa: E402

_SEVERITY_RANK = {"PASS": -1, "LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _worst_severity(severities) -> str:
    return max(severities, key=_SEVERITY_RANK.__getitem__, default="PASS")


def _decision_exit(decision: Decision, shadow: bool) -> int:
    code = 1 if decision in (Decision.BLOCK, Decision.QUARANTINE) else 0
    return 0 if shadow and code == 1 else code


def _verdict_to_dict(v, table_decision: TableDecision) -> dict:
    return {
        "table": v.ref.table,
        "urn": v.ref.urn,
        "file_path": v.file_path,
        "severity": v.severity,
        "changed_columns": [{"name": c.name, "kind": c.kind.value} for c in v.columns],
        "affected": [
            {"urn": a.urn, "name": a.name, "kind": a.kind, "owner": a.owner, "reason": a.reason}
            for a in v.affected
        ],
        "message": v.message,
        "why": [
            {
                "rule": w.rule,
                "urn": w.urn,
                "kind": w.kind,
                "hops": w.hops,
                "detail": w.detail,
            }
            for w in v.why
        ],
        "column_suspects": list(v.column_suspects),
        "decision": table_decision.decision.value,
        "contract_evaluations": [
            {
                "contract_id": evaluation.contract_id,
                "column": evaluation.column,
                "change_kind": evaluation.change_kind.value,
                "policy": evaluation.policy,
                "outcome": evaluation.outcome,
                "model_urn": evaluation.model_urn,
                "deployment_urn": evaluation.deployment_urn,
                "semantic": evaluation.semantic,
                "reason": evaluation.reason,
            }
            for evaluation in table_decision.evaluations
        ],
    }


def git_diff(repo: Path, base: str, head: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", f"{base}...{head}", "--", "*.sql"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def git_show(repo: Path, rev: str, path: str) -> str:
    """Read a file as it exists at ``rev`` (not the working tree)."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _collect_lineage_warnings(ref, file, results) -> list[CatalogWarning]:
    """Loud warnings when the catalog walk is empty — not silent 'safe'."""
    warnings: list[CatalogWarning] = []
    owners = {r.urn: [] for r in results}
    envs = {r.urn: "" for r in results}
    ml = find_ml_impacts(results, owners, envs)
    if not results:
        warnings.append(no_downstream_at_all(ref.urn, ref.table))
    elif not ml:
        warnings.append(no_ml_lineage(ref.urn, ref.table))
    return warnings


async def run(args: argparse.Namespace) -> int:
    cfg = Config()
    # --commit implies re-check after write (refuse silent "committed but untrue")
    want_verify = bool(args.verify) or bool(args.commit)
    do_commit = bool(args.commit) and not cfg.dry_run
    shadow = bool(args.shadow)
    repo = Path(args.repo)
    table_map_path = Path(args.table_map)
    if not table_map_path.is_file():
        raise FileNotFoundError(
            f"table map not found: {table_map_path} — run seed/verify_graph.py first"
        )
    table_map = load_table_map(table_map_path)
    contracts = load_contracts(Path(args.contracts))

    diff_text = git_diff(repo, args.base, args.head)
    if not diff_text.strip():
        print("no SQL changes in diff — PASS")
        return 0

    gateway = DataHubGateway(cfg)
    state = StateStore(cfg.state_db)
    await state.init()
    agent = Agent(cfg)

    verdicts = []
    table_decisions: list[TableDecision] = []
    proposals = []
    warnings: list[CatalogWarning] = []
    changed_files = list(parse_diff(diff_text))

    for file in changed_files:
        ref = table_map.get(file.file_path)
        if ref is None:
            print(f"SKIP (unmapped): {file.file_path}")
            warnings.append(unmapped_sql_file(file.file_path))
            continue
        sql = git_show(repo, args.head, file.file_path)
        results = gateway.downstream(ref, max_hops=4)
        table_warnings = _collect_lineage_warnings(ref, file, results)
        warnings.extend(table_warnings)
        table_decision = evaluate_table(ref.urn, file.columns, results, table_warnings, contracts)
        owners = {r.urn: gateway.owners(r.urn) for r in results}
        envs = {r.urn: gateway.environment(r.urn) for r in results}
        verdict = compute_verdict(ref, file, results, owners, envs)
        verdicts.append(verdict)
        table_decisions.append(table_decision)
        source = f"PR #{args.pr} ({args.head})"
        proposals += await plan_writebacks(file, ref, sql, gateway, source)
        proposals += await plan_term_drift(file, ref, sql, gateway, source)

    for v in verdicts:
        print(f"{v.ref.table}: {v.severity} — {v.message}")
        if v.column_suspects:
            print(f"  column_suspects: {', '.join(v.column_suspects)}")

    for w in warnings:
        print(f"WARN [{w.code}]: {w.message}")
        print(f"  remedy: {w.remedy}")

    if do_commit:
        for v in verdicts:
            try:
                gateway.stamp_reviewed(v.ref.urn, pr=str(args.pr))
            except Exception:
                pass

    if do_commit:
        # Re-plan immediately before write so we only commit still-real gaps.
        fresh: list = []
        for file in changed_files:
            ref = table_map.get(file.file_path)
            if ref is None:
                continue
            sql = git_show(repo, args.head, file.file_path)
            source = f"PR #{args.pr} ({args.head}) pre-commit"
            fresh += await plan_writebacks(file, ref, sql, gateway, source)
            fresh += await plan_term_drift(file, ref, sql, gateway, source)
        run_id = f"{args.repo}:{args.pr}:{args.head}"
        apply_results = await apply_proposals(fresh, gateway, state, run_id)
        committed = [p for p, s, _ in apply_results if s == "COMMITTED"]
        skipped = [p for p, s, _ in apply_results if s == "SKIPPED"]
        blocked = [(p, w) for p, s, w in apply_results if s == "BLOCKED_EMPTY"]
        print(f"COMMITTED {len(committed)} write-back(s)")
        if skipped:
            print(f"SKIPPED {len(skipped)} already-applied write-back(s)")
        if blocked:
            print(f"BLOCKED_EMPTY {len(blocked)} unsafe empty lineage write(s) refused")
            for _p, w in blocked:
                if w:
                    warnings.append(w)
                    print(f"WARN [{w.code}]: {w.message}")
                    print(f"  remedy: {w.remedy}")
        proposals = fresh
    else:
        print(f"dry-run: {len(proposals)} proposal(s) would be written after merge")

    if want_verify:
        remaining = 0
        for file in changed_files:
            ref = table_map.get(file.file_path)
            if ref is None:
                continue
            sql = git_show(repo, args.head, file.file_path)
            remaining += len(
                await plan_writebacks(file, ref, sql, gateway, f"PR #{args.pr} (verify)")
            )
        if remaining == 0:
            print(
                f"VERIFIED: no remaining lineage gaps from this plan "
                f"({len(proposals)} proposal(s) considered)"
            )
        else:
            print(f"VERIFY FAILED: {remaining} missing edge(s) remain")
            if do_commit:
                print(
                    "WARN: commit finished but graph re-check still sees gaps — "
                    "do not treat empty/partial writes as success."
                )
            return 2

    decision = worst_decision(d.decision for d in table_decisions)
    summary = await agent.summarize(
        {
            "verdicts": [
                _verdict_to_dict(verdict, decision)
                for verdict, decision in zip(verdicts, table_decisions)
            ],
            "decision": decision.value,
            "proposals": [p.__dict__ for p in proposals],
            "warnings": [w.to_dict() for w in warnings],
        }
    )
    comment = render_comment(
        verdicts,
        proposals,
        dry_run=not do_commit,
        author=args.author,
        summary=summary,
        shadow=shadow,
        warnings=warnings,
        decision=decision,
        table_decisions=table_decisions,
    )
    print(comment)

    if args.comment_out:
        Path(args.comment_out).write_text(comment, encoding="utf-8")
    if args.notify_out:
        payload = build_notify_payload(verdicts, pr=str(args.pr))
        payload["decision"] = decision.value
        payload["contract_evaluations"] = [
            evaluation
            for verdict, decision in zip(verdicts, table_decisions)
            for evaluation in _verdict_to_dict(verdict, decision)["contract_evaluations"]
        ]
        out = Path(args.notify_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"wrote notify payload → {out}")
    if args.json:
        worst = _worst_severity(v.severity for v in verdicts)
        payload = {
            "verdict": worst,
            "decision": decision.value,
            "tables": [
                _verdict_to_dict(verdict, table_decision)
                for verdict, table_decision in zip(verdicts, table_decisions)
            ],
            "proposals": [p.__dict__ for p in proposals],
            "warnings": [w.to_dict() for w in warnings],
            "dry_run": not do_commit,
            "shadow": shadow,
            "why": [
                why
                for verdict, table_decision in zip(verdicts, table_decisions)
                for why in _verdict_to_dict(verdict, table_decision)["why"]
            ],
            "column_suspects": sorted({s for v in verdicts for s in v.column_suspects}),
            "notify": build_notify_payload(verdicts, pr=str(args.pr)),
        }
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    code = _decision_exit(decision, shadow)
    if shadow and decision in (Decision.BLOCK, Decision.QUARANTINE):
        print(f"SHADOW: would block ({decision.value}) but exiting 0")
    return code


def main() -> int:
    cfg = Config()
    parser = argparse.ArgumentParser(
        description="Trueline PR guard",
        epilog=(
            "Workflow: seed_ml_tail → verify_graph → MCP up → run_local. "
            "Empty lineage is never treated as silent success. "
            "--commit re-plans before write and implies post-write --verify."
        ),
    )
    parser.add_argument("--repo", default=str(ROOT), help="git repo root (default: this repo)")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--author", default=None)
    parser.add_argument("--table-map", default=str(ROOT / "demo_repo" / "table_map.json"))
    parser.add_argument("--contracts", default=str(cfg.contracts_path))
    parser.add_argument(
        "--commit",
        action="store_true",
        help="apply write-backs (post-merge only); re-plans first; implies verify",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="re-query graph for remaining lineage gaps (auto-on with --commit)",
    )
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="comment CRITICAL/HIGH but exit 0 (brownfield adoption)",
    )
    parser.add_argument("--json", default=None, help="write machine-readable verdict to path")
    parser.add_argument("--comment-out", default=None, help="write PR comment markdown to path")
    parser.add_argument(
        "--notify-out",
        default=None,
        help="write dry-run on-call notify payload JSON (owners from graph)",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary: fail loudly, no fakes
        print(f"FATAL: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

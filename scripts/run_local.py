#!/usr/bin/env python
"""Trueline guard pipeline for local/CI diffs (primary demo path).

Usage examples:
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847 --commit --verify
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
from trueline.comment import render_comment  # noqa: E402
from trueline.config import Config, load_table_map  # noqa: E402
from trueline.datahub_client import DataHubGateway  # noqa: E402
from trueline.diff_parser import parse_diff  # noqa: E402
from trueline.impact import compute_verdict  # noqa: E402
from trueline.state import StateStore  # noqa: E402
from trueline.writeback import apply_proposals, plan_term_drift, plan_writebacks  # noqa: E402

SEVERITY_EXIT = {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 0, "PASS": 0}


def _verdict_to_dict(v) -> dict:
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


async def run(args: argparse.Namespace) -> int:
    cfg = Config()
    # --commit only applies when dry-run is off (env TRUELINE_DRY_RUN=false)
    do_commit = bool(args.commit) and not cfg.dry_run
    repo = Path(args.repo)
    table_map_path = Path(args.table_map)
    if not table_map_path.is_file():
        raise FileNotFoundError(
            f"table map not found: {table_map_path} — run seed/verify_graph.py first"
        )
    table_map = load_table_map(table_map_path)
    gateway = DataHubGateway(cfg)
    state = StateStore(cfg.state_db)
    await state.init()
    agent = Agent(cfg)

    diff_text = git_diff(repo, args.base, args.head)
    if not diff_text.strip():
        print("no SQL changes in diff — PASS")
        return 0

    verdicts = []
    proposals = []
    for file in parse_diff(diff_text):
        ref = table_map.get(file.file_path)
        if ref is None:
            print(f"SKIP (unmapped): {file.file_path}")
            continue
        # Use PR head SQL so write-back planning reflects the change under review.
        sql = git_show(repo, args.head, file.file_path)
        results = gateway.downstream(ref, max_hops=4)
        owners = {r.urn: gateway.owners(r.urn) for r in results}
        envs = {r.urn: gateway.environment(r.urn) for r in results}
        verdict = compute_verdict(ref, file, results, owners, envs)
        verdicts.append(verdict)
        source = f"PR #{args.pr} ({args.head})"
        proposals += await plan_writebacks(file, ref, sql, gateway, source)
        proposals += await plan_term_drift(file, ref, sql, gateway, source)

    for v in verdicts:
        print(f"{v.ref.table}: {v.severity} — {v.message}")

    # Best-effort stamp: every gated dataset was reviewed by Trueline on this PR.
    for v in verdicts:
        try:
            gateway.stamp_reviewed(v.ref.urn, pr=str(args.pr))
        except Exception:
            pass

    if do_commit:
        run_id = f"{args.repo}:{args.pr}:{args.head}"
        results = await apply_proposals(proposals, gateway, state, run_id)
        committed = [p for p, s in results if s == "COMMITTED"]
        skipped = [p for p, s in results if s == "SKIPPED"]
        print(f"COMMITTED {len(committed)} write-back(s)")
        if skipped:
            print(f"SKIPPED {len(skipped)} already-applied write-back(s)")
    else:
        print(f"dry-run: {len(proposals)} proposal(s) would be written after merge")

    if args.verify:
        remaining = 0
        for file in parse_diff(diff_text):
            ref = table_map.get(file.file_path)
            if ref is None:
                continue
            sql = git_show(repo, args.head, file.file_path)
            remaining += len(await plan_writebacks(file, ref, sql, gateway, f"PR #{args.pr} (verify)"))
        if remaining == 0:
            print(f"VERIFIED: lineage gap closed ({len(proposals)} edge(s) now in the graph)")
        else:
            print(f"VERIFY FAILED: {remaining} missing edge(s) remain")
            return 2

    # Already inside asyncio.run — await directly (do not open a nested loop).
    summary = await agent.summarize(
        {
            "verdicts": [_verdict_to_dict(v) for v in verdicts],
            "proposals": [p.__dict__ for p in proposals],
        }
    )
    comment = render_comment(
        verdicts,
        proposals,
        dry_run=not do_commit,
        author=args.author,
        summary=summary,
    )
    print(comment)

    if args.comment_out:
        Path(args.comment_out).write_text(comment, encoding="utf-8")
    if args.json:
        worst = max((v.severity for v in verdicts), default="PASS")
        payload = {
            "verdict": worst,
            "tables": [_verdict_to_dict(v) for v in verdicts],
            "proposals": [p.__dict__ for p in proposals],
            "dry_run": not do_commit,
        }
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    worst = max((v.severity for v in verdicts), default="LOW")
    return SEVERITY_EXIT.get(worst, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trueline PR guard")
    parser.add_argument("--repo", default=str(ROOT), help="git repo root (default: this repo)")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--author", default=None)
    parser.add_argument("--table-map", default=str(ROOT / "demo_repo" / "table_map.json"))
    parser.add_argument("--commit", action="store_true", help="apply write-backs (post-merge only)")
    parser.add_argument("--verify", action="store_true", help="re-query graph after commit")
    parser.add_argument("--json", default=None, help="write machine-readable verdict to path")
    parser.add_argument("--comment-out", default=None, help="write PR comment markdown to path")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary: fail loudly, no fakes
        print(f"FATAL: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

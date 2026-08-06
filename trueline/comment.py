from __future__ import annotations

import re

from .decision import Decision, TableDecision
from .impact import TableVerdict
from .writeback import Proposal

_SEV_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _node_id(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", label).strip("_")
    return cleaned or "node"


def _readout(verdict: TableVerdict, author: str | None) -> str:
    lines = ["```"]
    for col in verdict.columns:
        lines.append(
            f"  {verdict.ref.table}.{col.name:<28} {col.kind.value:<10} "
            + (f"author: @{author}" if author else "")
        )
    if verdict.column_suspects:
        lines.append(f"  column_suspects: {', '.join(verdict.column_suspects)}")
    for a in verdict.affected:
        lines.append(
            f"  └─ {a.name:<28} {a.kind:<16} {a.reason}"
            + (f" owner: @{a.owner}" if a.owner else "")
        )
    lines.append(f"  VERDICT: {verdict.severity} — {verdict.message}")
    lines.append("```")
    return "\n".join(lines)


def render_blast_radius(verdicts: list[TableVerdict]) -> str:
    """Mermaid flowchart of changed tables → downstream ML entities (graph facts only)."""
    if not verdicts:
        return ""
    lines = [
        "### Blast radius",
        "",
        "```mermaid",
        "flowchart LR",
    ]
    broken_ids: list[str] = []
    seen_edges: set[tuple[str, str]] = set()
    seen_nodes: set[str] = set()

    def add_node(nid: str, label: str, broken: bool = False) -> None:
        if nid in seen_nodes:
            return
        seen_nodes.add(nid)
        safe = label.replace('"', "'")
        # Palette-locked (DESIGN.md §1.1b): lime = hot path, never a second hue.
        if broken:
            lines.append(f'  {nid}["{safe}"]:::broken')
            broken_ids.append(nid)
        else:
            lines.append(f'  {nid}["{safe}"]:::safe')

    for v in verdicts:
        src = _node_id(v.ref.table)
        drops = [c.name for c in v.columns if c.kind.value == "DROP"]
        label = v.ref.table
        if drops:
            label = f"{v.ref.table}\\nDROP {', '.join(drops)}"
        add_node(src, label, broken=bool(drops) or v.severity == "CRITICAL")

        # Order affected for a readable left-to-right path: feature → model → group/deploy
        order = {
            "MLFEATURE": 0,
            "MLMODEL": 1,
            "MLMODELGROUP": 2,
            "MLMODELDEPLOYMENT": 3,
            "DASHBOARD": 4,
        }
        ordered = sorted(v.affected, key=lambda a: order.get(a.kind, 9))
        prev = src
        for a in ordered:
            nid = _node_id(a.name)
            node_label = a.name
            if a.kind == "MLMODELDEPLOYMENT":
                node_label = f"{a.name}\\n(deployment)"
            add_node(nid, node_label, broken=v.severity == "CRITICAL" and a.kind.startswith("ML"))
            edge = (prev, nid)
            if edge not in seen_edges:
                seen_edges.add(edge)
                if v.severity == "CRITICAL":
                    lines.append(f"  {prev} -.->|risk| {nid}")
                else:
                    lines.append(f"  {prev} --> {nid}")
            prev = nid

    # Tokens: --hot-node-* / --safe-node-* / --accent (#82C200) from DESIGN.md
    lines.append(
        "  classDef broken fill:#0A0A0A,stroke:#82C200,color:#FFFFFF,stroke-width:2px"
    )
    lines.append("  classDef safe fill:#000000,stroke:#404040,color:#A3A3A3")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_counterfactual(verdicts: list[TableVerdict]) -> str:
    """What-if-we-merge section from graph facts only (no invented metrics)."""
    if not verdicts:
        return ""
    worst = max(verdicts, key=lambda v: _SEV_RANK[v.severity])
    deploys = sorted({
        a.name for v in verdicts for a in v.affected if a.kind == "MLMODELDEPLOYMENT"
    })
    models = sorted({
        a.name for v in verdicts for a in v.affected if a.kind == "MLMODEL"
    })
    owners = sorted({
        a.owner for v in verdicts for a in v.affected if a.owner
    })
    suspects = sorted({s for v in verdicts for s in v.column_suspects})
    lines = [
        "### What if we merge?",
        "",
        f"- **Severity if merged:** `{worst.severity}`",
    ]
    if models:
        lines.append(f"- **Models in the blast radius:** {', '.join(f'`{m}`' for m in models)}")
    if deploys:
        lines.append(
            f"- **Online endpoints that would serve scores:** "
            f"{', '.join(f'`{d}`' for d in deploys)}"
        )
    if suspects:
        lines.append(f"- **Column suspects:** {', '.join(f'`{s}`' for s in suspects)}")
    if owners:
        lines.append(f"- **Owners to notify:** {', '.join(f'@{o}' for o in owners)}")
    if worst.severity == "CRITICAL":
        lines.append(
            "- **Outcome:** silent production degradation risk — block merge until reviewed."
        )
    elif worst.severity == "LOW":
        lines.append("- **Outcome:** safe to merge from an ML-breakage perspective (additive only).")
    else:
        lines.append("- **Outcome:** review consumers before merge.")
    lines.append("")
    return "\n".join(lines)


def render_notify(verdicts: list[TableVerdict]) -> str:
    """Owner page-out block (dry-run style; facts from ownership aspects)."""
    owners = sorted({a.owner for v in verdicts for a in v.affected if a.owner})
    if not owners:
        return ""
    worst = max(verdicts, key=lambda v: _SEV_RANK[v.severity]).severity
    if worst not in ("CRITICAL", "HIGH"):
        return ""
    lines = [
        "### Notify (dry-run page-out)",
        "",
        f"- cc {', '.join(f'@{o}' for o in owners)}",
        f"- severity: `{worst}`",
        "- channel: `#ml-oncall` (payload also available via `--notify-out`)",
        "",
    ]
    return "\n".join(lines)


def build_notify_payload(verdicts: list[TableVerdict], pr: str) -> dict:
    owners = sorted({a.owner for v in verdicts for a in v.affected if a.owner})
    worst = max(
        (v.severity for v in verdicts),
        key=_SEV_RANK.__getitem__,
        default="PASS",
    )
    return {
        "channel": "#ml-oncall",
        "text": f"Trueline {worst} on PR #{pr}",
        "severity": worst,
        "pr": pr,
        "owners": owners,
        "mentions": [f"@{o}" for o in owners],
        "tables": [v.ref.table for v in verdicts],
        "column_suspects": sorted({s for v in verdicts for s in v.column_suspects}),
        "deployments": sorted({
            a.name for v in verdicts for a in v.affected if a.kind == "MLMODELDEPLOYMENT"
        }),
    }


def render_contract_decisions(
    verdicts: list[TableVerdict],
    decision: Decision | None,
    table_decisions: list[TableDecision],
) -> str:
    if decision is None:
        return ""
    lines = ["### Contract decision", "", f"- Overall: `{decision.value}`"]
    for verdict, table_decision in zip(verdicts, table_decisions):
        lines.append(f"- `{verdict.ref.table}`: `{table_decision.decision.value}`")
        for evaluation in table_decision.evaluations:
            lines.append(
                f"  - `{evaluation.contract_id}` / `{evaluation.column}`: "
                f"`{evaluation.outcome}` - {evaluation.reason}"
            )
    lines.append("")
    return "\n".join(lines)


def render_comment(
    verdicts: list[TableVerdict],
    proposals: list[Proposal],
    dry_run: bool,
    author: str | None = None,
    summary: str | None = None,
    shadow: bool = False,
    decision: Decision | None = None,
    table_decisions: list[TableDecision] | None = None,
) -> str:
    worst = max(verdicts, key=lambda v: _SEV_RANK[v.severity], default=None)
    head = "PASS" if worst is None else worst.severity
    if shadow and head in ("CRITICAL", "HIGH"):
        title = f"## Trueline verdict — {head} (shadow mode — not blocking)"
    else:
        title = f"## Trueline verdict — {head}"
    out = [
        title,
        "",
        "Computed live from DataHub lineage (training data → features → models → deployments).",
        "",
    ]
    if summary:
        out += [summary, ""]
    decision_block = render_contract_decisions(verdicts, decision, list(table_decisions or []))
    if decision_block:
        out.append(decision_block)
    blast = render_blast_radius(verdicts)
    if blast:
        out.append(blast)
    counter = render_counterfactual(verdicts)
    if counter:
        out.append(counter)
    notify = render_notify(verdicts)
    if notify:
        out.append(notify)
    for v in verdicts:
        out += [_readout(v, author), ""]
    if proposals:
        out += ["**Proposed write-backs** — applied only after merge (PR-as-approval):", ""]
        for p in proposals:
            kind = {"LINEAGE": "COLUMN LINEAGE", "GLOSSARY_TERM": "GLOSSARY TERM"}.get(p.kind, p.kind)
            out.append(f"- `{kind}` → {p.target_urn} — {p.source} — state **PROPOSED**")
        out.append("")
    if dry_run:
        out.append("_This run was dry-run: nothing was written to the graph._")
    else:
        out.append("_Write-back committed after merge: lineage is now in DataHub._")
    if shadow:
        out.append("_Shadow mode: CI would not block merge (exit 0)._")
    return "\n".join(out)

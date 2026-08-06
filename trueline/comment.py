from __future__ import annotations

from .impact import TableVerdict
from .writeback import Proposal

_SEV_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _readout(verdict: TableVerdict, author: str | None) -> str:
    lines = ["```"]
    for col in verdict.columns:
        lines.append(f"  {verdict.ref.table}.{col.name:<28} {col.kind.value:<10} "
                     + (f"author: @{author}" if author else ""))
    for a in verdict.affected:
        lines.append(f"  └─ {a.name:<28} {a.kind:<12} {a.reason}"
                     + (f" owner: @{a.owner}" if a.owner else ""))
    lines.append(f"  VERDICT: {verdict.severity} — {verdict.message}")
    lines.append("```")
    return "\n".join(lines)


def render_comment(
    verdicts: list[TableVerdict],
    proposals: list[Proposal],
    dry_run: bool,
    author: str | None = None,
    summary: str | None = None,
) -> str:
    worst = max(verdicts, key=lambda v: _SEV_RANK[v.severity], default=None)
    head = "PASS" if worst is None else worst.severity
    out = [
        f"## Trueline verdict — {head}",
        "",
        "Computed live from DataHub lineage (training data → features → models → deployments).",
        "",
    ]
    if summary:
        out += [summary, ""]
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
    return "\n".join(out)
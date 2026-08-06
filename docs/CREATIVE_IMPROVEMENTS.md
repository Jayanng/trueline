# Creative improvements

Ideas ranked by **judge wow / effort**. Status updated as implemented.

## Implemented

| # | Idea | Where |
|---|---|---|
| 1 | **Blast-radius Mermaid** in PR comment | `trueline/comment.py` → `render_blast_radius` |
| 2 | **What if we merge?** counterfactual | `render_counterfactual` (graph facts only) |
| 3 | **Green PR twin** | branch `demo/pr-safe-add` (ADD-only → LOW) |
| 4 | **Owner page-out** | notify block + `--notify-out` JSON payload |
| 5 | **Severity trail JSON** | `why: [{rule, urn, kind, hops}]` in verdict JSON |
| 6 | **column_suspects** | DROPs/TYPE_CHANGEs on verdict + comment readout |
| 7 | **Shadow mode** | `--shadow` exits 0 on CRITICAL/HIGH |

### Severity nuance (enables green PR)

- **CRITICAL** — non-additive change (DROP / TYPE_CHANGE) with ML downstream  
- **LOW** — additive-only, even if ML consumers exist (listed for awareness)

## Stretch / future

8. Multi-repo table map — monorepo + dbt package paths  
9. DataHub Cloud + hosted Action — remove self-hosted requirement  
10. Human-in-the-loop accept on write-backs via DataHub proposals (Cloud)  
11. Cost-of-silence narrative pack — one slide of industry silent-failure stories  

## Pitch-safe creative framing

- **“Immune system for production ML”** — PRs are antibodies.  
- “The catalog compounds: every merge is a truth injection.”  
- Agent tools the graph; model only writes English.

## Demo commands

```bash
# Red PR (CRITICAL + mermaid + notify)
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 \
  --json .trueline/verdict.json --comment-out .trueline/comment.md \
  --notify-out .trueline/notify.json

# Green PR twin (LOW / exit 0)
python scripts/run_local.py --repo . --base main --head demo/pr-safe-add --pr 2848

# Shadow mode (comment CRITICAL, exit 0)
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 --shadow
```

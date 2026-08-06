# Demo video script (≤3:00)

**Visual style:** terminal + DataHub UI. Lead with the red PR.

| Time | Shot | Spoken |
|---|---|---|
| 0:00–0:15 | Title card / black terminal | “Production ML doesn’t crash — it degrades silently. Trueline catches that on the pull request, using DataHub’s ML lineage.” |
| 0:15–0:35 | DataHub UI: model + deployment | “Here’s the live path: order data → feature_order_risk → fraud_model_v4 in PROD → fraud-scoring-endpoint.” |
| 0:35–1:20 | `git diff main...demo/pr-2847` + run_local | “An innocent PR drops return_date. We run the guard.” Show command and CRITICAL exit. |
| 1:20–2:00 | PR comment full screen | Zoom verdict: CRITICAL, owner @datahub, feature → model → deployment. “Computed live — not a canned comment.” |
| 2:00–2:30 | Optional: `--commit --verify` or skill folder | “After merge, Trueline writes missing column lineage back — every PR makes the graph truer.” |
| 2:30–2:55 | Architecture one-liner | “MCP for reads, SDK for writes, LLM only for prose. Severity is deterministic.” |
| 2:55–3:00 | End card: repo URL | “Trueline — Production ML Agents track.” |

## Commands to record

```bash
# Ensure graph is healthy
python seed/verify_graph.py

# Wow moment
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 --author maya \
  --comment-out .trueline/comment.md --json .trueline/verdict.json

# Optional moment 2 (writes to graph — use a throwaway instance or accept lineage fill)
TRUELINE_DRY_RUN=false python scripts/run_local.py --repo . --base main --head demo/pr-2847 \
  --pr 2847 --commit --verify
```

## Do not show

- Invented metrics (null rates, latency)
- Claiming the ML tail is production customer data (it’s demo metadata)

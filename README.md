# Trueline — gate pull requests on DataHub ML lineage

Trueline is a **production-ML guard agent**: at pull-request time it walks DataHub’s
live ML lineage (training/feature data → features → models → deployments) via the
**MCP Server** (+ Python SDK), names the prod models a change would silently break,
and — after merge — writes missing column lineage back from the PR’s own SQL.

Every PR leaves the catalog more true than it found it.

Built for **Build with DataHub — The Agent Hackathon** · primary track
**Production ML Agents**. Apache 2.0.

## Website (5 pages)

Marketing site in `web/` — no in-site video (YouTube external only):

| Route | Content |
|---|---|
| `/` | Landing — thesis + live-shaped CRITICAL readout |
| `/guard` | Engine pipeline, severity, red/green PR, CLI |
| `/lineage` | ML path, seed, MCP/GMS/SDK reads & writes |
| `/skill` | `datahub-pr-guard` OSS skill |
| `/start` | Runbook (seed, env, commands) |

```bash
cd web && npm install && npm run dev
```

## The three demo moments

1. **The red PR** — dropping `return_date` turns a PR **CRITICAL**: it hits
   `feature_order_risk` → `fraud_model_v4` [PROD] → `fraud-scoring` group +
   `fraud-scoring-endpoint` deployment (owner `@datahub`).
2. **The graph gets truer** — on merge (`--commit --verify`), Trueline infers column
   lineage from the PR SQL and writes it back with provenance.
3. **Reviewed stamp** — gated datasets get `trueline.reviewed` (structured property)
   so the catalog records which entities passed the agent.

## Full ML path (demo tail)

The showcase-ecommerce pack ships **zero** ML entities. We graft a real (SDK-written)
demo tail:

`order_items` → `feature_order_risk` → **MLFeature** → **MLModel** → **Group** + **Deployment**

## Setup (reproduce from scratch)

```bash
pip install --upgrade acryl-datahub
datahub docker quickstart
datahub datapack load showcase-ecommerce
# UI http://localhost:9002 (datahub/datahub) → Settings → Access Tokens → create
# paste token into .env (see .env.example)
python seed/seed_ml_tail.py
# optional: datahub properties upsert -f seed/props.yaml
python seed/verify_graph.py
# start MCP sidecar (see ARCHITECTURE.md)
python -m mcp_server_datahub   # or your existing MCP process on :8000
```

## Run the guard

```bash
# Red PR (CRITICAL) — drop return_date
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 \
  --json .trueline/verdict.json --comment-out .trueline/comment.md --notify-out .trueline/notify.json

# Green PR twin (LOW) — additive notes only
python scripts/run_local.py --repo . --base main --head demo/pr-safe-add --pr 2848

# Shadow mode — comment CRITICAL but exit 0 (brownfield)
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 --shadow
```

Dry-run by default: proposes, writes nothing. `--commit --verify` applies after merge
and re-queries the graph to prove the gap closed. Exit codes: **0 PASS · 1 BLOCK · 2 error**.
PR comments include a Mermaid blast-radius diagram, “what if we merge?”, and owner notify hints.

Optional LLM prose (does **not** affect severity):

```env
GMI_API_KEY=...
GMI_BASE_URL=https://api.gmi-serving.com/v1
GMI_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

Without a key, comments render from engine facts only.

## OSS contribution

`skill/datahub-pr-guard` — non-interactive PR gate skill for
`datahub-project/datahub-skills` (composes lineage + enrich with an ML-aware severity
model). PR link: <LINK after opening>.

## Honesty notes

- The ML tail is **demo metadata** grafted with real SDK calls (pack has zero ML).
- Verdicts are computed **live** from the graph — no canned severity.
- LLM may only phrase the comment; it never invents lineage, owners, or severity.

## Criteria map

| Criterion | Where |
|---|---|
| Use of DataHub | MCP reads + SDK lineage/write + structured property + skill |
| Technical Execution | Deterministic engine + optional LLM prose; live e2e |
| Originality | PR-gated ML lineage + SQL write-back |
| Real-World Usefulness | Silent model degradation caught before merge |
| Submission Quality | README, demo video, reproducible setup |
| Bonus OSS | `datahub-pr-guard` skill |

## License

Apache 2.0 — see LICENSE.

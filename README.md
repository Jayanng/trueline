# Trueline: Production AI Change Firewall

Trueline is a **Production AI Change Firewall**. At pull-request time it walks
DataHub's live ML lineage (training/feature data → features → models → deployments)
via the **MCP Server** (+ Python SDK), evaluates changed columns against versioned
**Model Change Contracts**, and names the production models a change could silently
break. After merge, it can write missing column lineage back from the PR's own SQL.

Every PR leaves the catalog more true than it found it.

Model Change Contracts identify protected model inputs and the expected model and
deployment evidence. Severity describes blast radius; the independent decision says
what CI must do:

| Decision | Meaning |
|---|---|
| `ALLOW` | Sufficient evidence and no contract violation; additive-only changes remain `LOW` |
| `REVIEW` | Generic non-contract downstream impact needs a human review; existing severity is retained |
| `BLOCK` | A non-additive protected input change violates a contract with verified model and deployment evidence |
| `QUARANTINE` | Expected model, deployment, or catalog evidence is missing; restore or seed the named evidence and rerun |

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

**Sharp edges (do not skip):** empty lineage is **not** “safe to merge.” Wrong
`table_map` URNs, MCP down, or a bad seed can yield zero downstream — Trueline
emits structured `WARN` codes (`NO_ML_LINEAGE`, `NO_DOWNSTREAM`) instead of
failing silently. Lineage **commits with empty column maps are refused**
(`BLOCKED_EMPTY`) so a thin write cannot wipe richer fine-grained edges.

```bash
pip install --upgrade acryl-datahub
datahub docker quickstart
datahub datapack load showcase-ecommerce
# UI http://localhost:9002 (datahub/datahub) → Settings → Access Tokens → create
# paste token into .env (see .env.example)
# Existing fraud example, optional:
python seed/seed_ml_tail.py
# optional: datahub properties upsert -f seed/props.yaml
python seed/verify_graph.py          # must print VERIFY OK for the fraud example

# Synthetic clinical contract graph:
python seed/seed_clinical_tail.py
python seed/verify_clinical_graph.py # must print VERIFY CLINICAL OK

# start MCP sidecar (see ARCHITECTURE.md)
python -m mcp_server_datahub   # or your existing MCP process on :8000

# Run only from a clean worktree; this refuses dirty workspaces:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_clinical_demo_branches.ps1 -Base main
```

**Correct artifact workflow**

1. Start DataHub quickstart and load the showcase datapack.
2. Optionally run `seed_ml_tail.py` and `verify_graph.py` for the existing fraud example.
3. Run `seed_clinical_tail.py`.
4. Run `verify_clinical_graph.py`; continue only after `VERIFY CLINICAL OK`.
5. Start MCP and confirm it is listening on `MCP_SERVER_URL`.
6. From a clean worktree, run `setup_clinical_demo_branches.ps1`.
7. Run the unsafe and safe guard commands below. SQL always comes from **git head** (`git show`), not the dirty working tree.

`--commit` still re-plans before write and **implies** post-write gap verification.

## Run the guard

```bash
# Unsafe clinical PR: CRITICAL severity, BLOCK decision
python scripts/run_local.py --repo . --base main --head demo/sepsis-unsafe --pr 3001 \
  --contracts contracts/model-change-contracts.json --json .trueline/sepsis-unsafe.json

# Safe clinical PR: LOW severity, ALLOW decision
python scripts/run_local.py --repo . --base main --head demo/sepsis-safe --pr 3002 \
  --contracts contracts/model-change-contracts.json --json .trueline/sepsis-safe.json

# Shadow mode reports a blocking decision but exits 0 (brownfield)
python scripts/run_local.py --repo . --base main --head demo/sepsis-unsafe --pr 3001 \
  --contracts contracts/model-change-contracts.json --shadow
```

Dry-run by default: proposes, writes nothing. `--commit --verify` applies after merge
and re-queries the graph to prove the gap closed. Exit codes: **0 ALLOW/REVIEW · 1 BLOCK/QUARANTINE · 2 error**.
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
- The clinical graph is **synthetic metadata only**. It contains no patient records or real clinical endpoint.
- Trueline evaluates metadata change risk. It does **not** diagnose patients or provide medical advice.
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

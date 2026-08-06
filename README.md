# Trueline — gate pull requests on DataHub ML lineage

Trueline reads DataHub's end-to-end ML lineage (training data → features → models →
deployments) at pull-request time, names the prod models a change silently breaks,
and — after the PR merges — writes the missing column lineage back to the graph from
the PR's own SQL. Every PR leaves the catalog more true than it found it.

Built for **Build with DataHub — The Agent Hackathon** · primary track
**Production ML Agents**. Apache 2.0.

## The three demo moments

1. **The red PR** — an innocent-looking drop (`return_date`) turns a PR red: it nulls
   `feature_order_risk` → degrades `fraud_model_v4` in prod (owner @riya).
2. **The graph gets truer** — on merge, Trueline infers column lineage from the PR's
   SQL and writes it back with provenance.
3. **Governance drift caught** — a PII term (`customers.cust_email`) that never
   propagated is detected and proposed.

## Setup (reproduce from scratch)

```bash
pip install --upgrade acryl-datahub
datahub docker quickstart
datahub datapack load showcase-ecommerce
# UI http://localhost:9002 (datahub/datahub) -> Settings -> Access Tokens -> create
# paste token into .env (see .env.example)
python seed/seed_ml_tail.py        # grafts the DEMO ML tail (the pack ships zero ML entities)
python seed/verify_graph.py        # ground-truth checks
```

## Run the guard

```bash
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847
```

Dry-run by default: proposes, writes nothing. `--commit --verify` applies after merge
and re-queries the graph to prove the gap closed. Exit codes: 0 PASS · 1 BLOCK ·
2 error. On GitHub, the Action runs the same CLI (self-hosted runner — hosted runners
cannot reach a local quickstart).

## OSS contribution

`skill/datahub-pr-guard` — a new skill for `datahub-project/datahub-skills`
(non-interactive PR gate composing `datahub-lineage` + `datahub-enrich` with an
ML-aware severity model). PR link: <LINK> (insert after opening the PR).

## Honesty notes

- The ML tail (`feature_order_risk`, `fraud_model_v4`, `fraud-scoring`) is **demo
  metadata** grafted onto the official showcase-ecommerce datapack, which ships zero
  ML entities. Created with real SDK calls; labeled as demo entities in `seed/README.md`.
- Every verdict is computed live from the graph. No canned comments, no invented
  metrics (no null-rate or latency numbers anywhere).
- Without `ANTHROPIC_API_KEY` the agent runs in heuristic mode: comments render from
  engine facts; nothing is fabricated.

## Criteria map

| Criterion | Where |
|---|---|
| Use of DataHub | SDK reads + SDK writes + MCP (agent layer) + structured property + new skill |
| Technical Execution | deterministic engine + LLM prose split; e2e-tested pipeline |
| Originality | PR-gated ML lineage + write-back from PR SQL |
| Real-World Usefulness | silent model degradation caught before merge |
| Submission Quality | this README, demo video, reproducible setup |
| Bonus OSS | `datahub-pr-guard` skill PR |

## License

Apache 2.0 — see LICENSE.
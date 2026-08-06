# Devpost draft — Trueline

## Elevator pitch (≤280 chars)

Trueline is a production-ML guard agent: on every data PR it walks DataHub’s live ML lineage (via MCP) so a silent column drop can’t degrade fraud models unnoticed — then writes missing lineage back so the catalog gets more true with every merge.

## Inspiration

Production ML fails quietly. Models don’t crash when a dbt column disappears — features null out, fraud scores drift, and money bleeds for weeks. DataHub is the only place the full path (training data → features → models → deployments) is a graph. We put an agent on the PR — the moment ground truth is known.

## What it does

1. **Parses the PR diff** (SQL/dbt) into changed columns.
2. **Walks downstream lineage** on a live DataHub instance (MCP + SDK).
3. **Scores severity ML-first**: any path to MLFeature / MLModel / Group / Deployment = **CRITICAL**.
4. **Comments on the PR** with owners, path, and proposed write-backs (dry-run).
5. **After merge**, commits column lineage from the PR’s SQL and stamps `trueline.reviewed`.

Demo: drop `return_date` → CRITICAL on `fraud_model_v4` + `fraud-scoring-endpoint`.

## How we built it

- **Deterministic engine** (diff → lineage → severity → write-back planner) — never lets the LLM invent facts.
- **MCP Server** for catalog reads (`get_lineage`, `search`, `get_entities`).
- **Python SDK** for lineage writes and ML aspect edges.
- **Optional GMI Cloud DeepSeek Flash** for PR comment prose only.
- **OSS skill** `datahub-pr-guard` for the DataHub skills ecosystem.
- Demo ML tail grafted onto official showcase-ecommerce (honestly labeled).

## Challenges

- Showcase pack has **zero** ML entities — we seed a real tail with SDK emits.
- MCP `get_lineage` shapes and `max_hops>2` quirks — dual path with SDK + aspect walk.
- ML URNs are 3-part; short forms are invalid.
- Hosted GitHub runners can’t reach local quickstart — primary demo is `run_local.py`.

## Accomplishments

- Live CRITICAL verdict against real DataHub + MCP.
- Full track path including **deployment**.
- Engine/LLM separation with honest dry-run defaults.
- Reproducible seed + verify scripts.

## What we learned

- The PR is the highest-leverage moment for lineage truth.
- Agents for production ML must be **tool-first, prose-second**.
- Composing DataHub beats reimplementing a catalog.

## What’s next

- Column-level fine-grained lineage filters in severity.
- Managed DataHub Cloud demo for hosted Actions.
- Upstream skill merge + broader SQL dialect coverage.

## Built with

DataHub Core · MCP Server · acryl-datahub SDK · Python · sqlglot · GMI Cloud DeepSeek · GitHub Actions

## Track

**Production ML Agents**

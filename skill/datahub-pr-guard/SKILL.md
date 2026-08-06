---
name: datahub-pr-guard
description: Non-interactive PR/CI gate that checks a pull request's SQL/schema changes against DataHub ML lineage before merge. Use when a pull request or diff changes dbt models, SQL views, or table columns and you need to know which downstream ML features, models, deployments, and dashboards are affected — or to propose backfilling missing column lineage from the PR's own SQL. Composes datahub-lineage and datahub-enrich with an ML-aware severity model and emits a machine-readable verdict. Triggers on: "gate this PR", "what does this PR break", "check this diff against the catalog", "PR guard".
user-invocable: true
min-cli-version: 1.5.0.1rc1
allowed-tools:
  - Bash(datahub *)
---

# datahub-pr-guard

## Multi-Agent Compatibility

- **Non-interactive by design:** made for CI runs, PR bots, and agents that must not prompt. Never asks a follow-up question.
- **Deterministic first:** severity and blast radius come from the graph, not from the model. The LLM may phrase the verdict but must never invent lineage facts.
- **Idempotent:** re-running the same PR produces the same verdict and skips already-applied write-backs.

## Not This Skill

| If you need to... | Use... |
|---|---|
| Explore lineage interactively, ask "what feeds this dashboard" | `datahub-lineage` |
| Enrich an entity with tags/terms/owners ad hoc | `datahub-enrich` |
| Gate a PR / CI run on ML lineage and emit a verdict | **`datahub-pr-guard`** (this skill) |
| Backfill column lineage from a PR's SQL after merge | **`datahub-pr-guard`** (write-back step) |

## Prerequisites

- A reachable DataHub instance (Core quickstart or Cloud) with `DATAHUB_GMS_URL` and `DATAHUB_GMS_TOKEN` set.
- `datahub` CLI ≥ 1.5.0.1rc1.
- The diff of the PR: `git diff <base>...<head> -- '*.sql'`.

## Step 1: Parse the diff into changed SQL files

Use `git diff` and keep only modified `.sql` files. For each file, list the changed
column names: lines starting with `-` are DROPs, `+` are ADDs; same name on both
sides with different types is a TYPE_CHANGE.

```bash
git -C <repo> diff <base>...<head> -- '*.sql'
```

## Step 2: Resolve each file to a DataHub dataset

Map the repo-relative path to a dataset URN (project manifest or convention), then verify the entity exists:

```bash
datahub get --urn "urn:li:dataset:(urn:li:dataPlatform:snowflake,<db>.<schema>.<table>,PROD)"
```

If the entity does not exist, note it and continue — Trueline still reports the change.

## Step 3: Walk lineage downstream from each changed table

For each changed column, trace downstream through DataHub ML lineage (datasets → features → models → deployments):

```bash
datahub lineage path --from "urn:li:dataset:(...)" --to "urn:li:mlModel:..." --format json
# or MCP tools: get_lineage / get_lineage_paths_between
```

## Step 4: Apply the ML-first severity model

Use the rules in `references/severity-model.md`:
- **CRITICAL** — a non-additive change has an ML entity (`urn:li:mlModel:*`, `urn:li:mlFeature:*`, `urn:li:mlFeatureTable:*`, `urn:li:mlPrimaryKey:*`, `urn:li:mlModelGroup:*`, `urn:li:mlModelDeployment:*`) downstream.
- **HIGH** — downstream dashboards/BI consumers (looker, tableau, powerbi, superset).
- **MEDIUM** — multiple downstream consumers, or any non-additive change.
- **LOW** — additive-only changes, including changes with ML entities downstream.

Owners come from the entities' ownership aspect — never invented. Name them in the verdict.

Apply the contract decision independently of severity:

- **ALLOW** — evidence is sufficient and no protected-input policy is violated. Additive-only changes remain `LOW` / `ALLOW`.
- **BLOCK** — a contracted critical input has a non-additive change prohibited by its policy, and both the contracted model and deployment are verified in lineage.
- **QUARANTINE** — an expected contracted model, deployment, or catalog lineage signal is missing. Name the missing evidence and the remedy; never treat empty lineage as safe.
- **REVIEW** — a non-additive changed column has downstream lineage but no matching protected input. Preserve the severity computed from its generic blast radius.

## Step 5: Emit the machine-readable verdict

Output the verdict as `trueline-verdict.json` (schema in `templates/pr-verdict.template.md`):

```json
{
  "verdict": "CRITICAL",
  "decision": "BLOCK",
  "tables": [
    {
      "table": "ORDER_ITEMS",
      "urn": "urn:li:dataset:(...)",
      "severity": "CRITICAL",
      "decision": "BLOCK",
      "affected": [
        {"urn": "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)", "kind": "MLMODEL", "owner": "datahub", "env": "PROD"},
        {"urn": "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,fraud-scoring-endpoint,PROD)", "kind": "MLMODELDEPLOYMENT", "env": "PROD"}
      ]
    }
  ],
  "dry_run": true
}
```

For a PR comment, render `templates/pr-verdict.template.md` with the same facts.

## Step 6: Write-back (post-merge only — the PR is the approval)

Before merge: nothing is written; the verdict lists **PROPOSED** write-backs. After
merge: for each SQL change, derive column mappings from the PR's own SQL and backfill
missing column lineage:

```bash
datahub lineage path --from <upstream> --to <downstream> --format json  # check what exists
```

Then add the missing column lineage via the SDK (`add_lineage` with a column map) —
`datahub` CLI has no column-lineage add command. Propagation of glossary terms
(e.g. PII drifting downstream) uses the entity update pattern. Record every write in
the state journal (SQLite) so re-runs are `SKIPPED`.

## References

- `references/severity-model.md` — the ML-first severity rules and examples.
- `templates/pr-verdict.template.md` — verdict JSON schema and PR comment template.
- Shipped skills it composes: `datahub-lineage`, `datahub-enrich`.

## Common Mistakes

- Using the LLM to compute severity — always deterministic from the graph.
- Writing lineage before merge — dry-run until the PR merges.
- Adding column lineage for ML entities via `add_lineage` — ML edges are aspect fields; column lineage is Dataset → Dataset only.
- Claiming owners/env without reading the ownership/instance aspects.

## Red Flags

- The graph returns no lineage at all for a table the PR changes — say so; do not assume it is safe.
- The PR SQL references a table that is not in the catalog — flag the gap, do not invent it.
- Severity claims without a lineage path — every CRITICAL must cite the path.
- Collapsing severity and decision into one value — report both, using contract evidence only for the decision.

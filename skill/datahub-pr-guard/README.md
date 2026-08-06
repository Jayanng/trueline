# datahub-pr-guard

Non-interactive PR/CI gate for DataHub ML lineage. Part of the Trueline project
(see `ARCHITECTURE.md` in the repo root). Composes `datahub-lineage` + `datahub-enrich`
with an ML-aware severity model; emits a machine-readable verdict; backfills missing
column lineage from the PR's own SQL after merge (PR-as-approval).

Install with the DataHub skills flow: `npx skills add datahub-project/datahub-skills`
(after this PR merges).
# Seed scripts

These scripts graft demo ML tails onto the official `showcase-ecommerce` datapack
(which ships **zero** ML entities). Entities are real DataHub metadata written via
real SDK/MCP emits and explicitly labeled synthetic. The clinical graph contains no
patient records or real endpoint, and Trueline does not diagnose patients.

## Path (Production ML Agents track)

```
order_items (training/feature data)
  → feature_order_risk (feature table)
    → MLFeature feature_order_risk
      → MLModel fraud_model_v4 [PROD] owner @datahub
         ├→ MLModelGroup fraud-scoring
         └→ MLModelDeployment fraud-scoring-endpoint [PROD]
```

Column lineage on `order_items → feature_order_risk` is **intentionally table-only**
so Trueline can demonstrate write-back after merge.

## Scripts

| Script | Role |
|---|---|
| `seed_ml_tail.py` | Creates dataset, feature, model, group, deployment + table lineage |
| `verify_graph.py` | Ground-truth checks; fails nonzero if the ML path is broken |
| `seed_clinical_tail.py` | Creates the synthetic sepsis contract graph and intentional column-lineage gap |
| `verify_clinical_graph.py` | Requires the exact clinical model/deployment path; prints `VERIFY CLINICAL OK` |
| `props.yaml` | `trueline.reviewed` structured property definition |
| `recipes/` | Optional file-based dataset recipe (fallback) |

## Workflow (order matters)

Empty catalog reads are **not** treated as success by the guard. Always:

1. Start DataHub quickstart and load the showcase datapack.
2. Optionally run `python seed/seed_ml_tail.py` and `python seed/verify_graph.py` for the existing fraud example; require `VERIFY OK`.
3. Run `python seed/seed_clinical_tail.py`.
4. Run `python seed/verify_clinical_graph.py`; require `VERIFY CLINICAL OK`.
5. Start MCP.
6. From a clean worktree, run `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_clinical_demo_branches.ps1 -Base main`.
7. Run `scripts/run_local.py` against `demo/sepsis-unsafe` and `demo/sepsis-safe` with `contracts/model-change-contracts.json`.

If either verifier fails, fix the seed, URNs, or MCP connectivity before running the
guard. Empty lineage is never evidence that a change is safe.

## Reset

```bash
datahub datapack unload showcase-ecommerce
datahub datapack load showcase-ecommerce
python seed/seed_ml_tail.py
# optional: datahub properties upsert -f seed/props.yaml
python seed/verify_graph.py
```

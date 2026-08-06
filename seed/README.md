# Seed scripts

These scripts graft the **demo ML tail** onto the official `showcase-ecommerce`
datapack (which ships **zero** ML entities). Entities are real DataHub metadata
written via real SDK/MCP emits — labeled as demo so judges know what is synthetic.

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
| `props.yaml` | `trueline.reviewed` structured property definition |
| `recipes/` | Optional file-based dataset recipe (fallback) |

## Reset

```bash
datahub datapack unload showcase-ecommerce
datahub datapack load showcase-ecommerce
python seed/seed_ml_tail.py
# optional: datahub properties upsert -f seed/props.yaml
python seed/verify_graph.py
```

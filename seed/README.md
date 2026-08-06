# Seed scripts

- `recipes/` — file-based ingestion recipe that creates the `FEATURE_ORDER_RISK` dataset (the official `showcase-ecommerce` datapack ships **zero ML entities**).
- `seed_ml_tail.py` — grafts the demo ML tail: dataset → MLFeature `feature_order_risk` → MLModel `fraud_model_v4` (owner @riya, env PROD) → MLModelGroup `fraud-scoring`. All entities are **demo metadata** created via real SDK calls; the product story is real, the entities are synthetic.
- `props.yaml` — `trueline.reviewed` structured property.
- `verify_graph.py` — ground-truth checks; exit code 0 = demo graph is healthy.

Reset: `datahub datapack unload showcase-ecommerce && datahub datapack load showcase-ecommerce`, then re-run `seed_ml_tail.py` + `verify_graph.py`.
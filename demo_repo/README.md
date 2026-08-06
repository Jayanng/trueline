# Demo repo

The PR under test. `main` holds a healthy dbt-style project; `demo/pr-2847` is the PR
that silently breaks the fraud model.

- `models/order_items.sql` — drops `return_date` (innocent-looking cleanup; actually nulls the fraud feature).
- `models/feature_order_risk.sql` — adds `customer_email` joined from `customers` (PII drift surface).

Run: `python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847`
(The `--repo` flag points at the trueline repo root, where this directory lives.)

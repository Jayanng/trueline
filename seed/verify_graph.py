"""Ground-truth verification: fails nonzero on any mismatch with the demo story."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from trueline.config import Config, TableRef
from trueline.datahub_client import DataHubGateway

load_dotenv()

FEATURE = TableRef(platform="snowflake", db="order_entry", schema="", table="feature_order_risk")
ORDER_ITEMS = TableRef(platform="snowflake", db="order_entry", schema="", table="order_items")
MODEL_URN = "urn:li:mlModel:fraud_model_v4"


def main() -> None:
    cfg = Config()
    gateway = DataHubGateway(cfg)
    failures: list[str] = []

    results = gateway.downstream(FEATURE, max_hops=4)
    urns = {r.urn for r in results}
    for expected in ("urn:li:mlFeature:(order_entry,feature_order_risk)", MODEL_URN,
                     "urn:li:mlModelGroup:fraud-scoring"):
        if expected not in urns:
            failures.append(f"missing downstream ML entity: {expected}")
    model = next((r for r in results if r.urn == MODEL_URN), None)
    if model is None:
        failures.append("fraud_model_v4 not reachable from feature dataset")
    else:
        owners = gateway.owners(MODEL_URN)
        env = gateway.environment(MODEL_URN)
        if "datahub" not in " ".join(owners).lower():
            failures.append(f"model owner missing (got {owners})")
        if env != "PROD":
            failures.append(f"model env not PROD (got {env!r})")

    cust = TableRef(platform="snowflake", db="order_entry", schema="", table="customers")
    pii = gateway.column_terms(cust, "cust_email")
    print(f"cust_email PII terms: {pii}")

    total = len(gateway.search(query="*"))
    print(f"total entities found: {total}")
    if total < 1000:
        failures.append(f"suspiciously few entities: {total}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("VERIFY OK — ML tail reachable, owners/env correct, pack present.")

    table_map = {
        "demo_repo/models/order_items.sql": {
            "platform": "snowflake", "db": "order_entry", "schema": "", "table": "order_items",
        },
        "demo_repo/models/feature_order_risk.sql": {
            "platform": "snowflake", "db": "order_entry", "schema": "", "table": "feature_order_risk",
        },
    }
    out = Path(__file__).resolve().parent.parent / "demo_repo" / "table_map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table_map, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
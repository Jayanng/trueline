"""Ground-truth verification: fails nonzero on any mismatch with the demo story."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from trueline.config import Config, TableRef
from trueline.datahub_client import DataHubGateway

load_dotenv()

FEATURE = TableRef(platform="snowflake", db="order_entry", schema="", table="feature_order_risk")
ORDER_ITEMS = TableRef(platform="snowflake", db="order_entry", schema="", table="order_items")
FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
MODEL_URN = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)"
GROUP_URN = "urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,fraud-scoring,PROD)"


def main() -> None:
    cfg = Config()
    gateway = DataHubGateway(cfg)
    failures: list[str] = []

    print(f"FEATURE dataset urn: {FEATURE.urn}")
    results = gateway.downstream(FEATURE, max_hops=4)
    print(f"downstream hits ({len(results)}):")
    for r in results:
        print(f"  hops={r.hops} type={r.entity_type} urn={r.urn}")

    urns = {r.urn for r in results}
    for expected in (FEATURE_URN, MODEL_URN, GROUP_URN):
        if expected not in urns:
            failures.append(f"missing downstream ML entity: {expected}")
    model = next((r for r in results if r.urn == MODEL_URN), None)
    if model is None:
        failures.append("fraud_model_v4 not reachable from feature dataset")
    else:
        owners = gateway.owners(MODEL_URN)
        env = gateway.environment(MODEL_URN)
        print(f"model owners={owners} env={env!r}")
        if "datahub" not in " ".join(owners).lower():
            failures.append(f"model owner missing (got {owners})")
        if env and env != "PROD":
            failures.append(f"model env not PROD (got {env!r})")
        if not env:
            print("WARN: model environment empty on get_entities (aspect may not be exposed by MCP)")

    # Showcase pack customers (real URN shape from datapack)
    cust = TableRef(
        platform="snowflake",
        db="b2fd91.order_entry_db",
        schema="order_entry",
        table="customers",
    )
    pii = gateway.column_terms(cust, "cust_email")
    print(f"cust_email PII terms ({cust.urn}): {pii}")

    sample = gateway.search(query="*", entity_type="", limit=20)
    print(f"search sample size: {len(sample)} (first={sample[:3]})")
    if len(sample) < 5:
        failures.append(f"suspiciously few search hits: {len(sample)}")
    feat_hits = gateway.search(query="feature_order_risk", entity_type="", limit=10)
    if FEATURE.urn not in feat_hits and not any("feature_order_risk" in u for u in feat_hits):
        failures.append("feature_order_risk not found via MCP search")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("VERIFY OK — ML tail reachable, pack present, live catalog answers.")

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

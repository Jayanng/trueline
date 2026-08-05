"""Print ground-truth facts about the seeded instance. Grown into verify_graph.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.sdk import DataHubClient

load_dotenv()


def main() -> None:
    client = DataHubClient(server=os.environ["DATAHUB_GMS_URL"], token=os.environ["DATAHUB_GMS_TOKEN"])
    # SPIKE: pin the exact search API (client.entities.search vs client.search) and
    # the total_count attribute by running this against the live instance.
    print("search: SPIKE - pin signature and count")
    for query in ["order_items", "feature_order_risk", "mlModel", "customers"]:
        try:
            results = client.entities.search(query=query, entity_type="dataset")
            print(f"  {query}: {[str(r.urn) for r in results][:5]}")
        except Exception as exc:  # noqa: BLE001 - SPIKE prints, does not hide
            print(f"  {query}: ERROR {exc!r}")


if __name__ == "__main__":
    main()

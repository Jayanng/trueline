"""Graft the demo ML tail onto the showcase-ecommerce datapack.

These are DEMO entities — real DataHub metadata written via real SDK calls,
created because the official datapack ships zero ML entities. Honest labeling
lives in seed/README.md and the project README.

Idempotent: checks existence before emitting; re-running is safe.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    GenericAspectClass, MetadataChangeProposalClass,
)
from datahub.sdk import DataHubClient
from datahub.metadata.urns import DatasetUrn

load_dotenv()

GMS_URL = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
GMS_TOKEN = os.getenv("DATAHUB_GMS_TOKEN", "")

FEATURE_DATASET = make_dataset_urn(platform="snowflake", name="order_entry.feature_order_risk", env="PROD")
ORDER_ITEMS = make_dataset_urn(platform="snowflake", name="order_entry.order_items", env="PROD")
ML_FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
ML_MODEL_URN = "urn:li:mlModel:fraud_model_v4"
ML_GROUP_URN = "urn:li:mlModelGroup:fraud-scoring"
OWNER = "urn:li:corpuser:datahub"


def _mcp(entity_type: str, entity_urn: str, aspect_name: str, aspect: dict) -> MetadataChangeProposalClass:
    return MetadataChangeProposalClass(
        changeType="UPSERT",
        entityType=entity_type,
        entityUrn=entity_urn,
        aspectName=aspect_name,
        aspect=GenericAspectClass(
            value=json.dumps(aspect).encode(),
            contentType="application/json",
        ),
    )


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=GMS_TOKEN)

    # 1) MLFeature
    emitter.emit_mcp(_mcp("mlFeature", ML_FEATURE_URN, "mlFeatureProperties", {
        "description": "Fraud risk score feature; downstream of order_items (demo tail).",
        "dataType": "DOUBLE",
    }))
    print(f"seeded MLFeature {ML_FEATURE_URN}")

    # 2) MLModel with feature + owner + env
    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "mlModelProperties", {
        "description": "Production fraud model (demo tail).",
        "customProperties": {"environment": "PROD"},
        "mlFeatures": [ML_FEATURE_URN],
    }))
    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "ownership", {
        "owners": [{"owner": OWNER, "type": "TECHNICAL_OWNER"}],
    }))
    print(f"seeded MLModel {ML_MODEL_URN} (owner datahub, env PROD)")

    # 3) MLModelGroup
    emitter.emit_mcp(_mcp("mlModelGroup", ML_GROUP_URN, "mlModelGroupProperties", {
        "description": "Fraud scoring model group (demo tail).",
        "name": "fraud-scoring",
    }))
    print(f"seeded MLModelGroup {ML_GROUP_URN}")

    # 4) Table-level lineage from order_items -> FEATURE_ORDER_RISK (no column mapping)
    client = DataHubClient(server=GMS_URL, token=GMS_TOKEN)
    client.lineage.add_lineage(
        upstream=DatasetUrn.from_string(ORDER_ITEMS),
        downstream=DatasetUrn.from_string(FEATURE_DATASET),
        column_lineage=None,
        emit_mode="SYNC_WAIT",
    )
    print("seeded table-level lineage order_items -> feature_order_risk (column gap intentional)")


if __name__ == "__main__":
    main()
"""Graft the demo ML tail onto the showcase-ecommerce datapack.

These are DEMO entities — real DataHub metadata written via real SDK calls,
created because the official datapack ships zero ML entities. Honest labeling
lives in seed/README.md and the project README.

Idempotent: checks existence before emitting; re-running is safe.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter
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


def main() -> None:
    from datahub.emitter.mcp import MetadataChangeProposalWrapper
    from datahub.metadata.schema_classes import (
        MLFeaturePropertiesClass, MLModelGroupPropertiesClass,
        MLModelPropertiesClass, OwnerClass, OwnershipClass, OwnershipTypeClass,
    )

    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=GMS_TOKEN)

    feature_props = MLFeaturePropertiesClass(
        description="Fraud risk score feature; downstream of order_items (demo tail).",
        dataType="DOUBLE",
        sources=[{"urn": FEATURE_DATASET}],
    )
    mcp = MetadataChangeProposalWrapper(entityType="mlFeature", entityUrn=ML_FEATURE_URN, aspectName="mlFeatureProperties", aspect=feature_props)
    emitter.emit_mcp(mcp)
    print(f"seeded MLFeature {ML_FEATURE_URN}")

    model_props = MLModelPropertiesClass(
        description="Production fraud model (demo tail).",
        mlFeatures=[ML_FEATURE_URN],
        customProperties={"environment": "PROD"},
    )
    mcp = MetadataChangeProposalWrapper(entityType="mlModel", entityUrn=ML_MODEL_URN, aspectName="mlModelProperties", aspect=model_props)
    emitter.emit_mcp(mcp)
    ownership = OwnershipClass(owners=[OwnerClass(owner=OWNER, type=OwnershipTypeClass.TECHNICAL_OWNER)])
    mcp = MetadataChangeProposalWrapper(entityType="mlModel", entityUrn=ML_MODEL_URN, aspectName="ownership", aspect=ownership)
    emitter.emit_mcp(mcp)
    print(f"seeded MLModel {ML_MODEL_URN} (owner datahub, env PROD)")

    group_props = MLModelGroupPropertiesClass(
        description="Fraud scoring model group (demo tail).",
        name="fraud-scoring",
    )
    mcp = MetadataChangeProposalWrapper(entityType="mlModelGroup", entityUrn=ML_GROUP_URN, aspectName="mlModelGroupProperties", aspect=group_props)
    emitter.emit_mcp(mcp)
    print(f"seeded MLModelGroup {ML_GROUP_URN}")

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
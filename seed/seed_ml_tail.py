"""Graft the demo ML tail onto the showcase-ecommerce datapack.

These are DEMO entities — real DataHub metadata written via real SDK calls,
created because the official datapack ships zero ML entities. Honest labeling
lives in seed/README.md and the project README.

Full track path:
  training/feature data (order_items → feature_order_risk)
  → MLFeature → MLModel → MLModelGroup + MLModelDeployment

Idempotent: re-running is safe.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.emitter.mce_builder import (
    make_dataset_urn,
    make_ml_model_deployment_urn,
    make_ml_model_group_urn,
    make_ml_model_urn,
)
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    GenericAspectClass,
    MetadataChangeProposalClass,
)
from datahub.sdk import DataHubClient
from datahub.metadata.urns import DatasetUrn

load_dotenv()

GMS_URL = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
GMS_TOKEN = os.getenv("DATAHUB_GMS_TOKEN", "")

FEATURE_DATASET = make_dataset_urn(platform="snowflake", name="order_entry.feature_order_risk", env="PROD")
ORDER_ITEMS = make_dataset_urn(platform="snowflake", name="order_entry.order_items", env="PROD")
ML_FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
ML_MODEL_URN = make_ml_model_urn(model_name="fraud_model_v4", platform="mlflow", env="PROD")
ML_GROUP_URN = make_ml_model_group_urn(group_name="fraud-scoring", platform="mlflow", env="PROD")
ML_DEPLOY_URN = make_ml_model_deployment_urn(
    platform="mlflow", deployment_name="fraud-scoring-endpoint", env="PROD"
)
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

    # 0) Feature dataset (training/feature input table for the ML tail)
    emitter.emit_mcp(_mcp("dataset", FEATURE_DATASET, "datasetKey", {
        "platform": "urn:li:dataPlatform:snowflake",
        "name": "order_entry.feature_order_risk",
        "origin": "PROD",
    }))
    emitter.emit_mcp(_mcp("dataset", FEATURE_DATASET, "datasetProperties", {
        "description": (
            "Fraud risk feature table (demo ML tail). Built from order_items training/"
            "feature data; source of MLFeature feature_order_risk."
        ),
        "name": "feature_order_risk",
        "customProperties": {"environment": "PROD", "trueline_role": "feature_table"},
    }))
    print(f"seeded dataset {FEATURE_DATASET}")

    # 1) MLFeature — sources=[FEATURE_DATASET] creates dataset→feature lineage
    emitter.emit_mcp(_mcp("mlFeature", ML_FEATURE_URN, "mlFeatureProperties", {
        "description": "Fraud risk score feature; downstream of order_items / feature_order_risk (demo tail).",
        "dataType": "CONTINUOUS",
        "sources": [FEATURE_DATASET],
    }))
    print(f"seeded MLFeature {ML_FEATURE_URN} (sources={FEATURE_DATASET})")

    # 2) MLModel with feature + group + deployment + owner + env
    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "mlModelProperties", {
        "description": "Production fraud model (demo tail).",
        "customProperties": {"environment": "PROD"},
        "mlFeatures": [ML_FEATURE_URN],
        "groups": [ML_GROUP_URN],
        "deployments": [ML_DEPLOY_URN],
    }))
    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "ownership", {
        "owners": [{"owner": OWNER, "type": "TECHNICAL_OWNER"}],
    }))
    print(f"seeded MLModel {ML_MODEL_URN} (owner datahub, env PROD)")

    # 3) MLModelGroup
    emitter.emit_mcp(_mcp("mlModelGroup", ML_GROUP_URN, "mlModelGroupProperties", {
        "description": "Fraud scoring model group (demo tail).",
        "name": "fraud-scoring",
        "customProperties": {"environment": "PROD"},
    }))
    print(f"seeded MLModelGroup {ML_GROUP_URN}")

    # 4) MLModelDeployment — completes training data → features → models → deployments
    emitter.emit_mcp(_mcp("mlModelDeployment", ML_DEPLOY_URN, "mlModelDeploymentProperties", {
        "description": "Online fraud-scoring endpoint in PROD (demo tail).",
        "customProperties": {
            "environment": "PROD",
            "endpoint": "https://fraud.example.internal/score",
            "model": ML_MODEL_URN,
        },
    }))
    print(f"seeded MLModelDeployment {ML_DEPLOY_URN}")

    # 5) Table-level lineage order_items -> feature_order_risk (column gap intentional)
    client = DataHubClient(server=GMS_URL, token=GMS_TOKEN)
    client.lineage.add_lineage(
        upstream=DatasetUrn.from_string(ORDER_ITEMS),
        downstream=DatasetUrn.from_string(FEATURE_DATASET),
        column_lineage=False,
    )
    print("seeded table-level lineage order_items -> feature_order_risk (column gap intentional)")
    print("ML path: order_items → feature_order_risk → feature → model → group + deployment")


if __name__ == "__main__":
    main()

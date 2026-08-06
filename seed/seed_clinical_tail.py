"""Seed a synthetic clinical ML lineage path in DataHub.

This script writes metadata only. It contains no patient records or real endpoint URL,
and is safe to run repeatedly because every write is an UPSERT.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datahub.emitter.mce_builder import (
    make_dataset_urn,
    make_ml_model_deployment_urn,
    make_ml_model_urn,
)
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import GenericAspectClass, MetadataChangeProposalClass
from datahub.metadata.urns import DatasetUrn
from datahub.sdk import DataHubClient
from dotenv import load_dotenv

load_dotenv()

GMS_URL = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
GMS_TOKEN = os.getenv("DATAHUB_GMS_TOKEN", "")

PATIENT_LABS_URN = make_dataset_urn("snowflake", "clinical.patient_labs", "PROD")
SEPSIS_FEATURES_URN = make_dataset_urn("snowflake", "clinical.sepsis_features", "PROD")
ML_FEATURE_URN = "urn:li:mlFeature:(clinical,lactate_trend)"
ML_MODEL_URN = make_ml_model_urn(model_name="sepsis_risk_v3", platform="mlflow", env="PROD")
ML_DEPLOY_URN = make_ml_model_deployment_urn(
    platform="mlflow", deployment_name="icu-early-warning", env="PROD"
)
OWNER_URN = "urn:li:corpuser:clinical-ml-oncall"
SYNTHETIC = {"environment": "PROD", "synthetic_demo_metadata": "true"}


def _mcp(entity_type: str, urn: str, aspect_name: str, aspect: dict) -> MetadataChangeProposalClass:
    return MetadataChangeProposalClass(
        changeType="UPSERT",
        entityType=entity_type,
        entityUrn=urn,
        aspectName=aspect_name,
        aspect=GenericAspectClass(value=json.dumps(aspect).encode(), contentType="application/json"),
    )


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=GMS_TOKEN)

    for urn, name, description in (
        (PATIENT_LABS_URN, "patient_labs", "Synthetic demo metadata for a patient laboratory table."),
        (SEPSIS_FEATURES_URN, "sepsis_features", "Synthetic demo metadata for sepsis model features."),
    ):
        emitter.emit_mcp(_mcp("dataset", urn, "datasetProperties", {
            "name": name,
            "description": description,
            "customProperties": SYNTHETIC,
        }))
        print(f"seeded synthetic dataset {urn}")

    emitter.emit_mcp(_mcp("mlFeature", ML_FEATURE_URN, "mlFeatureProperties", {
        "description": "Synthetic demo lactate trend feature.",
        "dataType": "CONTINUOUS",
        "sources": [SEPSIS_FEATURES_URN],
        "customProperties": SYNTHETIC,
    }))
    print(f"seeded synthetic MLFeature {ML_FEATURE_URN}")

    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "mlModelProperties", {
        "description": "Synthetic demo sepsis risk model metadata; not a clinical system.",
        "customProperties": SYNTHETIC,
        "mlFeatures": [ML_FEATURE_URN],
        "deployments": [ML_DEPLOY_URN],
    }))
    emitter.emit_mcp(_mcp("mlModel", ML_MODEL_URN, "ownership", {
        "owners": [{"owner": OWNER_URN, "type": "TECHNICAL_OWNER"}],
    }))
    print(f"seeded synthetic MLModel {ML_MODEL_URN}")

    emitter.emit_mcp(_mcp("mlModelDeployment", ML_DEPLOY_URN, "mlModelDeploymentProperties", {
        "description": "Synthetic demo ICU early-warning deployment metadata; no real endpoint.",
        "customProperties": {**SYNTHETIC, "model": ML_MODEL_URN},
    }))
    print(f"seeded synthetic MLModelDeployment {ML_DEPLOY_URN}")

    client = DataHubClient(server=GMS_URL, token=GMS_TOKEN)
    client.lineage.add_lineage(
        upstream=DatasetUrn.from_string(PATIENT_LABS_URN),
        downstream=DatasetUrn.from_string(SEPSIS_FEATURES_URN),
        column_lineage=False,
    )
    print("seeded table-level lineage patient_labs -> sepsis_features (column gap intentional)")


if __name__ == "__main__":
    main()

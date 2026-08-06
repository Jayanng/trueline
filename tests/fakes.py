from __future__ import annotations

from dataclasses import dataclass, field

from trueline.config import TableRef
from trueline.datahub_client import LineageResult

ORDER_ITEMS = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
FEATURE = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="FEATURE_ORDER_RISK")
CUSTOMERS = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="customers")
PATIENT_LABS = TableRef(platform="snowflake", db="clinical", schema="", table="patient_labs")
SEPSIS_FEATURES = TableRef(platform="snowflake", db="clinical", schema="", table="sepsis_features")

ML_FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
ML_MODEL_URN = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)"
ML_GROUP_URN = "urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,fraud-scoring,PROD)"
ML_DEPLOY_URN = "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,fraud-scoring-endpoint,PROD)"
CLINICAL_FEATURE_URN = "urn:li:mlFeature:(clinical,lactate_trend)"
CLINICAL_MODEL_URN = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)"
CLINICAL_DEPLOY_URN = "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)"

LINEAGE = {
    ORDER_ITEMS.urn: [
        LineageResult(urn=FEATURE.urn, entity_type="dataset", platform="snowflake",
                      name="FEATURE_ORDER_RISK", hops=1, paths=((ORDER_ITEMS.urn, FEATURE.urn),)),
        LineageResult(urn=ML_FEATURE_URN, entity_type="mlfeature", platform="mlflow",
                      name="feature_order_risk", hops=2,
                      paths=((ORDER_ITEMS.urn, FEATURE.urn, ML_FEATURE_URN),)),
        LineageResult(urn=ML_MODEL_URN, entity_type="mlmodel", platform="mlflow",
                      name="fraud_model_v4", hops=3,
                      paths=((ORDER_ITEMS.urn, FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN),)),
        LineageResult(urn=ML_GROUP_URN, entity_type="mlmodelgroup", platform="mlflow",
                      name="fraud-scoring", hops=4,
                      paths=((ORDER_ITEMS.urn, FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN, ML_GROUP_URN),)),
        LineageResult(urn=ML_DEPLOY_URN, entity_type="mlmodeldeployment", platform="mlflow",
                      name="fraud-scoring-endpoint", hops=4,
                      paths=((ORDER_ITEMS.urn, FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN, ML_DEPLOY_URN),)),
    ],
    FEATURE.urn: [
        LineageResult(urn=ML_FEATURE_URN, entity_type="mlfeature", platform="mlflow",
                      name="feature_order_risk", hops=1, paths=((FEATURE.urn, ML_FEATURE_URN),)),
        LineageResult(urn=ML_MODEL_URN, entity_type="mlmodel", platform="mlflow",
                      name="fraud_model_v4", hops=2, paths=((FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN),)),
        LineageResult(urn=ML_GROUP_URN, entity_type="mlmodelgroup", platform="mlflow",
                      name="fraud-scoring", hops=3,
                      paths=((FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN, ML_GROUP_URN),)),
        LineageResult(urn=ML_DEPLOY_URN, entity_type="mlmodeldeployment", platform="mlflow",
                      name="fraud-scoring-endpoint", hops=3,
                      paths=((FEATURE.urn, ML_FEATURE_URN, ML_MODEL_URN, ML_DEPLOY_URN),)),
    ],
    PATIENT_LABS.urn: [
        LineageResult(urn=SEPSIS_FEATURES.urn, entity_type="dataset", platform="snowflake",
                      name="sepsis_features", hops=1,
                      paths=((PATIENT_LABS.urn, SEPSIS_FEATURES.urn),)),
        LineageResult(urn=CLINICAL_FEATURE_URN, entity_type="mlfeature", platform="mlflow",
                      name="lactate_trend", hops=2,
                      paths=((PATIENT_LABS.urn, SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN),)),
        LineageResult(urn=CLINICAL_MODEL_URN, entity_type="mlmodel", platform="mlflow",
                      name="sepsis_risk_v3", hops=3,
                      paths=((PATIENT_LABS.urn, SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN,
                              CLINICAL_MODEL_URN),)),
        LineageResult(urn=CLINICAL_DEPLOY_URN, entity_type="mlmodeldeployment", platform="mlflow",
                      name="icu-early-warning", hops=4,
                      paths=((PATIENT_LABS.urn, SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN,
                              CLINICAL_MODEL_URN, CLINICAL_DEPLOY_URN),)),
    ],
    SEPSIS_FEATURES.urn: [
        LineageResult(urn=CLINICAL_FEATURE_URN, entity_type="mlfeature", platform="mlflow",
                      name="lactate_trend", hops=1,
                      paths=((SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN),)),
        LineageResult(urn=CLINICAL_MODEL_URN, entity_type="mlmodel", platform="mlflow",
                      name="sepsis_risk_v3", hops=2,
                      paths=((SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN, CLINICAL_MODEL_URN),)),
        LineageResult(urn=CLINICAL_DEPLOY_URN, entity_type="mlmodeldeployment", platform="mlflow",
                      name="icu-early-warning", hops=3,
                      paths=((SEPSIS_FEATURES.urn, CLINICAL_FEATURE_URN, CLINICAL_MODEL_URN,
                              CLINICAL_DEPLOY_URN),)),
    ],
}

TERMS = {
    (CUSTOMERS.urn, "cust_email"): ["urn:li:glossaryTerm:OrderEntry.PII"],
}

OWNERS = {ML_MODEL_URN: ["datahub"], CLINICAL_MODEL_URN: ["clinical-ml-oncall"]}
ENVS = {
    ML_MODEL_URN: "PROD",
    ML_DEPLOY_URN: "PROD",
    CLINICAL_MODEL_URN: "PROD",
    CLINICAL_DEPLOY_URN: "PROD",
}


@dataclass
class FakeGateway:
    seed: dict[str, list[LineageResult]] = field(default_factory=lambda: LINEAGE)
    terms: dict[tuple[str, str], list[str]] = field(default_factory=lambda: TERMS)
    writes: list[tuple] = field(default_factory=list)

    def downstream(self, ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]:
        results = [r for r in self.seed.get(ref.urn, []) if r.hops <= max_hops]
        if column is not None:
            return []
        return results

    def entity(self, urn: str) -> dict:
        return {"urn": urn}

    def owners(self, urn: str) -> list[str]:
        return OWNERS.get(urn, [])

    def environment(self, urn: str) -> str:
        if urn in ENVS:
            return ENVS[urn]
        for env in ("PROD", "DEV", "TEST", "STAGING"):
            if urn.endswith(f",{env})") or urn.endswith(f",{env}"):
                return env
        return ""

    def search(self, query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]:
        return [urn for urn in self.seed if query.lower() in urn.lower()][:limit]

    def column_terms(self, ref: TableRef, column: str) -> list[str]:
        return self.terms.get((ref.urn, column), [])

    def add_lineage(self, upstream: TableRef, downstream: TableRef,
                    column_lineage: dict[str, list[str]] | None = None, wait: bool = False) -> None:
        self.writes.append(("LINEAGE", upstream.urn, downstream.urn, column_lineage))

    def add_term(self, ref: TableRef, column: str, term_urn: str) -> None:
        self.writes.append(("TERM", ref.urn, column, term_urn))

    def stamp_reviewed(self, urn: str, pr: str, wait: bool = False) -> None:
        self.writes.append(("REVIEWED", urn, pr))

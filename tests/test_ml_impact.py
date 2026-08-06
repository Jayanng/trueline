from trueline.datahub_client import LineageResult
from trueline.ml_impact import MLImpact, find_ml_impacts, ml_kind

MODEL = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)"
FEATURE = "urn:li:mlFeature:(order_entry,feature_order_risk)"
GROUP = "urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,fraud-scoring,PROD)"
DATASET = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS,PROD)"


def test_ml_kind_by_urn_prefix():
    deploy = "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,fraud-scoring-endpoint,PROD)"
    assert ml_kind(MODEL) == "MLMODEL"
    assert ml_kind(FEATURE) == "MLFEATURE"
    assert ml_kind(GROUP) == "MLMODELGROUP"
    assert ml_kind(deploy) == "MLMODELDEPLOYMENT"
    assert ml_kind(DATASET) is None


def test_find_ml_impacts_orders_by_hops_and_dedupes():
    results = [
        LineageResult(urn=MODEL, entity_type="mlmodel", platform="mlflow", name="fraud_model_v4", hops=3),
        LineageResult(urn=MODEL, entity_type="mlmodel", platform="mlflow", name="fraud_model_v4", hops=5),
        LineageResult(urn=DATASET, entity_type="dataset", platform="snowflake", name="ORDER_ITEMS", hops=1),
    ]
    impacts = find_ml_impacts(results, {MODEL: ["datahub"]}, {MODEL: "PROD"})
    assert [i.urn for i in impacts] == [MODEL]
    assert impacts[0].owner == "datahub"
    assert impacts[0].env == "PROD"
    assert impacts[0].display() == "fraud_model_v4 [MLMODEL] [PROD] owner: @datahub"


def test_no_ml_no_impacts():
    results = [LineageResult(urn=DATASET, entity_type="dataset", platform="snowflake", name="ORDER_ITEMS", hops=1)]
    assert find_ml_impacts(results, {}, {}) == []
from trueline.config import TableRef
from trueline.datahub_client import LineageResult
from trueline.diff_parser import ChangedColumn, ChangedFile, ChangeKind
from trueline.impact import compute_verdict

REF = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
MODEL = "urn:li:mlModel:fraud_model_v4"
MLFEATURE = "urn:li:mlFeature:(order_entry,feature_order_risk)"
LOOKER = "urn:li:dataset:(urn:li:dataPlatform:looker,analytics.dashboard_x,PROD)"
DS2 = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ORDER_ENTRY_DB.ORDER_ENTRY.FCT_SALES,PROD)"


def _file(*columns):
    return ChangedFile(file_path="demo_repo/models/order_items.sql", columns=tuple(columns), is_sql=True)


def _ml_results():
    return [
        LineageResult(urn=MLFEATURE, entity_type="mlfeature", platform="mlflow", name="feature_order_risk", hops=2),
        LineageResult(urn=MODEL, entity_type="mlmodel", platform="mlflow", name="fraud_model_v4", hops=3),
    ]


def test_ml_downstream_is_critical():
    v = compute_verdict(REF, _file(ChangedColumn("return_date", ChangeKind.DROP)), _ml_results(), {MODEL: ["riya"]}, {MODEL: "PROD"})
    assert v.severity == "CRITICAL"
    assert v.affected[0].owner == "riya"
    assert any(a.urn == MODEL for a in v.affected)


def test_dashboard_downstream_is_high():
    results = [LineageResult(urn=LOOKER, entity_type="dataset", platform="looker", name="dashboard_x", hops=2)]
    v = compute_verdict(REF, _file(ChangedColumn("return_date", ChangeKind.DROP)), results, {}, {})
    assert v.severity == "HIGH"


def test_many_datasets_is_medium():
    results = [LineageResult(urn=DS2, entity_type="dataset", platform="snowflake", name="FCT_SALES", hops=1),
               LineageResult(urn=LOOKER, entity_type="dataset", platform="snowflake", name="FCT_ORDERS", hops=2)]
    v = compute_verdict(REF, _file(ChangedColumn("return_date", ChangeKind.DROP)), results, {}, {})
    assert v.severity == "MEDIUM"


def test_drop_with_no_lineage_is_medium():
    v = compute_verdict(REF, _file(ChangedColumn("return_date", ChangeKind.DROP)), [], {}, {})
    assert v.severity == "MEDIUM"


def test_additive_only_is_low():
    v = compute_verdict(REF, _file(ChangedColumn("customer_email", ChangeKind.ADD)), [], {}, {})
    assert v.severity == "LOW"
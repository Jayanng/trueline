from trueline.config import TableRef
from trueline.datahub_client import LineageResult
from trueline.diff_parser import ChangedColumn, ChangedFile, ChangeKind
from trueline.impact import Severity, compute_verdict

ORDER_ITEMS = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
FEATURE = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="FEATURE_ORDER_RISK")
ML_MODEL = "urn:li:mlModel:fraud_model_v4"
ML_FEATURE = "urn:li:mlFeature:(order_entry,feature_order_risk)"


def test_drop_return_date_impact():
    file = ChangedFile(
        file_path="demo_repo/models/feature_order_risk.sql",
        columns=(ChangedColumn(name="return_date", kind=ChangeKind.DROP),),
        is_sql=True,
    )
    results = [LineageResult(urn=ML_FEATURE, entity_type="mlfeature", platform="mlflow",
                             name="feature_order_risk", hops=1),
               LineageResult(urn=ML_MODEL, entity_type="mlmodel", platform="mlflow",
                             name="fraud_model_v4", hops=2)]
    verdict = compute_verdict(FEATURE, file, results, {ML_MODEL: ["riya"]}, {ML_MODEL: "PROD"})
    assert verdict.severity == Severity.CRITICAL
    assert any(a.urn == ML_MODEL for a in verdict.affected)
    assert "return_date" in verdict.message


def test_no_impact_unchanged():
    file = ChangedFile(file_path="demo_repo/models/unrelated.sql", columns=(), is_sql=True)
    results = [LineageResult(urn=ML_MODEL, entity_type="mlmodel", platform="mlflow",
                             name="fraud_model_v4", hops=2)]
    verdict = compute_verdict(ORDER_ITEMS, file, results, {ML_MODEL: ["riya"]}, {ML_MODEL: "PROD"})
    assert verdict.severity == Severity.LOW
    assert verdict.affected == []


def test_no_ml_no_results():
    file = ChangedFile(
        file_path="demo_repo/models/order_items.sql",
        columns=(ChangedColumn(name="return_date", kind=ChangeKind.DROP),),
        is_sql=True,
    )
    verdict = compute_verdict(ORDER_ITEMS, file, [], {}, {})
    assert verdict.severity == Severity.LOW
    assert "No downstream ML" in verdict.message


def test_high_for_unowned_model():
    file = ChangedFile(
        file_path="demo_repo/models/feature_order_risk.sql",
        columns=(ChangedColumn(name="return_date", kind=ChangeKind.DROP),),
        is_sql=True,
    )
    results = [LineageResult(urn=ML_MODEL, entity_type="mlmodel", platform="mlflow",
                             name="fraud_model_v4", hops=2)]
    verdict = compute_verdict(FEATURE, file, results, {ML_MODEL: []}, {ML_MODEL: "PROD"})
    assert verdict.severity == Severity.HIGH
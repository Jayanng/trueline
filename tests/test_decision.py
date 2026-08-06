from trueline.contracts import CriticalInput, ModelContract
from trueline.datahub_client import LineageResult
from trueline.decision import Decision, evaluate_table, worst_decision
from trueline.diff_parser import ChangeKind, ChangedColumn
from trueline.warnings import no_downstream_at_all

DATASET = "urn:li:dataset:(urn:li:dataPlatform:snowflake,clinical.patient_labs,PROD)"
MODEL = "urn:li:mlModel:(urn:li:dataPlatform:mlflow,sepsis_risk_v3,PROD)"
DEPLOYMENT = "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,icu-early-warning,PROD)"
CONTRACT = ModelContract(
    id="sepsis-risk-v3-prod",
    model_urn=MODEL,
    deployment_urn=DEPLOYMENT,
    critical_inputs=(CriticalInput(
        dataset_urn=DATASET,
        column="lactate_mmol_l",
        policy="NO_DROP_OR_TYPE_CHANGE",
        semantic="blood lactate in mmol/L",
    ),),
)
LINEAGE = [
    LineageResult(MODEL, "mlmodel", "mlflow", "sepsis_risk_v3", 2),
    LineageResult(DEPLOYMENT, "mlmodeldeployment", "mlflow", "icu-early-warning", 3),
]


def test_drop_of_verified_critical_input_blocks():
    result = evaluate_table(
        DATASET,
        (ChangedColumn("lactate_mmol_l", ChangeKind.DROP),),
        LINEAGE,
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.BLOCK
    assert result.evaluations[0].outcome == "VIOLATED"


def test_additive_critical_input_change_allows():
    result = evaluate_table(
        DATASET,
        (ChangedColumn("lactate_mmol_l", ChangeKind.ADD),),
        LINEAGE,
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.ALLOW
    assert result.evaluations[0].outcome == "SATISFIED"


def test_downstream_impact_without_matching_contract_requires_review():
    result = evaluate_table(
        DATASET,
        (ChangedColumn("notes", ChangeKind.DROP),),
        LINEAGE,
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.REVIEW


def test_unmatched_non_additive_change_alongside_protected_add_requires_review():
    result = evaluate_table(
        DATASET,
        (
            ChangedColumn("lactate_mmol_l", ChangeKind.ADD),
            ChangedColumn("notes", ChangeKind.DROP),
        ),
        LINEAGE,
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.REVIEW


def test_protected_input_without_lineage_is_quarantined():
    warning = no_downstream_at_all(DATASET, "patient_labs")
    result = evaluate_table(
        DATASET,
        (ChangedColumn("lactate_mmol_l", ChangeKind.DROP),),
        [],
        [warning],
        (CONTRACT,),
    )
    assert result.decision == Decision.QUARANTINE
    assert "lineage" in " ".join(result.reasons).lower()
    assert "catalog warning" in result.evaluations[0].reason.lower()
    assert "no_downstream" in result.evaluations[0].reason.lower()


def test_missing_contracted_deployment_is_quarantined():
    result = evaluate_table(
        DATASET,
        (ChangedColumn("lactate_mmol_l", ChangeKind.DROP),),
        LINEAGE[:1],
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.QUARANTINE
    assert DEPLOYMENT in result.evaluations[0].reason
    assert "missing deployment evidence" in result.evaluations[0].reason.lower()


def test_missing_contracted_model_is_distinguished_from_missing_deployment():
    result = evaluate_table(
        DATASET,
        (ChangedColumn("lactate_mmol_l", ChangeKind.DROP),),
        LINEAGE[1:],
        [],
        (CONTRACT,),
    )
    assert result.decision == Decision.QUARANTINE
    assert MODEL in result.evaluations[0].reason
    assert "missing model evidence" in result.evaluations[0].reason.lower()
    assert "missing deployment evidence" not in result.evaluations[0].reason.lower()


def test_decision_precedence_is_explicit():
    assert worst_decision([Decision.ALLOW, Decision.BLOCK, Decision.REVIEW]) == Decision.BLOCK
    assert worst_decision([Decision.BLOCK, Decision.QUARANTINE]) == Decision.QUARANTINE

from trueline.comment import build_notify_payload, render_blast_radius, render_comment
from trueline.config import TableRef
from trueline.diff_parser import ChangedColumn, ChangeKind
from trueline.impact import AffectedEntity, TableVerdict
from trueline.writeback import Proposal

REF = TableRef(platform="snowflake", db="order_entry", schema="", table="order_items")


def _verdict():
    return TableVerdict(
        ref=REF,
        file_path="demo_repo/models/order_items.sql",
        columns=(ChangedColumn("return_date", ChangeKind.DROP),),
        severity="CRITICAL",
        affected=(
            AffectedEntity(
                "urn:li:mlFeature:(order_entry,feature_order_risk)",
                "feature_order_risk",
                "MLFEATURE",
                None,
                "downstream MLFEATURE",
            ),
            AffectedEntity(
                "urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)",
                "fraud_model_v4",
                "MLMODEL",
                "datahub",
                "downstream MLMODEL",
            ),
            AffectedEntity(
                "urn:li:mlModelDeployment:(urn:li:dataPlatform:mlflow,fraud-scoring-endpoint,PROD)",
                "fraud-scoring-endpoint",
                "MLMODELDEPLOYMENT",
                None,
                "downstream MLMODELDEPLOYMENT",
            ),
        ),
        message="silent prod-model breakage — dropping return_date reaches fraud_model_v4 [PROD]",
        column_suspects=("return_date",),
    )


def test_comment_contains_verdict_and_owner():
    text = render_comment([_verdict()], [], dry_run=True, author="maya")
    assert "Trueline verdict — CRITICAL" in text
    assert "fraud_model_v4" in text
    assert "owner: @datahub" in text
    assert "dry-run" in text.lower()


def test_comment_lists_proposals_and_skips_in_commit_mode():
    p = Proposal("LINEAGE", REF.urn, {"upstream": "u", "mapping": {"risk_score": ["order_total"]}}, "PR #2847")
    text = render_comment([_verdict()], [p], dry_run=False)
    assert "PROPOSED" in text
    assert "nothing was written" not in text.lower()
    assert "Write-back committed after merge" in text


def test_blast_radius_mermaid():
    text = render_blast_radius([_verdict()])
    assert "```mermaid" in text
    assert "flowchart LR" in text
    assert "order_items" in text
    assert "fraud_model_v4" in text
    assert "fraud-scoring-endpoint" in text
    assert "classDef broken" in text
    assert "#82C200" in text  # brand lime, not a second alert hue
    assert "classDef safe" in text


def test_comment_counterfactual_and_notify():
    text = render_comment([_verdict()], [], dry_run=True)
    assert "What if we merge?" in text
    assert "fraud-scoring-endpoint" in text
    assert "Notify (dry-run page-out)" in text
    assert "cc @datahub" in text
    assert "column_suspects" in text


def test_notify_payload():
    payload = build_notify_payload([_verdict()], pr="2847")
    assert payload["severity"] == "CRITICAL"
    assert "datahub" in payload["owners"]
    assert "fraud-scoring-endpoint" in payload["deployments"]
    assert "return_date" in payload["column_suspects"]


def test_shadow_banner():
    text = render_comment([_verdict()], [], dry_run=True, shadow=True)
    assert "shadow mode" in text.lower()

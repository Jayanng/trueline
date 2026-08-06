from trueline.comment import render_comment
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
            AffectedEntity("urn:li:mlModel:(urn:li:dataPlatform:mlflow,fraud_model_v4,PROD)", "fraud_model_v4", "MLMODEL",
                           "riya", "downstream ML entity"),
        ),
        message="silent prod-model breakage — downstream ML entity",
    )


def test_comment_contains_verdict_and_owner():
    text = render_comment([_verdict()], [], dry_run=True, author="maya")
    assert "Trueline verdict — CRITICAL" in text
    assert "fraud_model_v4" in text
    assert "owner: @riya" in text
    assert "dry-run" in text.lower()


def test_comment_lists_proposals_and_skips_in_commit_mode():
    p = Proposal("LINEAGE", REF.urn, {"upstream": "u", "mapping": {"risk_score": ["order_total"]}}, "PR #2847")
    text = render_comment([_verdict()], [p], dry_run=False)
    assert "PROPOSED" in text
    assert "nothing was written" not in text.lower()
    assert "Write-back committed after merge" in text
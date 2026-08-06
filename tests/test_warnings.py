import subprocess
import sys

from trueline.warnings import (
    empty_lineage_mapping_refused,
    no_downstream_at_all,
    no_ml_lineage,
    unmapped_sql_file,
)

from scripts.run_local import _collect_lineage_warnings
from trueline.config import TableRef
from trueline.datahub_client import LineageResult
from trueline.diff_parser import ChangedFile


def test_warning_codes_and_remedies():
    w = no_ml_lineage("urn:li:dataset:(urn:li:dataPlatform:snowflake,x,PROD)", "x")
    assert w.code == "NO_ML_LINEAGE"
    assert "verify_graph" in w.remedy
    assert w.to_dict()["urn"].startswith("urn:li:dataset:")

    d = no_downstream_at_all("urn:li:dataset:(urn:li:dataPlatform:snowflake,y,PROD)", "y")
    assert d.code == "NO_DOWNSTREAM"

    e = empty_lineage_mapping_refused("down", "up")
    assert e.code == "EMPTY_LINEAGE_REFUSED"
    assert "wipe" in e.message.lower() or "replace" in e.message.lower()

    u = unmapped_sql_file("demo_repo/models/foo.sql")
    assert u.code == "UNMAPPED_SQL_FILE"
    assert "table_map" in u.remedy


def test_empty_lineage_walk_emits_no_downstream_warning():
    ref = TableRef("snowflake", "order_entry", "", "order_items")
    file = ChangedFile("demo_repo/models/order_items.sql", (), is_sql=True)

    warnings = _collect_lineage_warnings(ref, file, [])

    assert [warning.code for warning in warnings] == ["NO_DOWNSTREAM"]
    assert warnings[0].urn == ref.urn


def test_non_ml_lineage_walk_emits_no_ml_warning():
    ref = TableRef("snowflake", "order_entry", "", "order_items")
    file = ChangedFile("demo_repo/models/order_items.sql", (), is_sql=True)
    downstream = [
        LineageResult(
            urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,order_entry.orders,PROD)",
            entity_type="dataset",
            platform="snowflake",
            name="orders",
            hops=1,
        )
    ]

    warnings = _collect_lineage_warnings(ref, file, downstream)

    assert [warning.code for warning in warnings] == ["NO_ML_LINEAGE"]
    assert "verify_graph" in warnings[0].remedy


def test_production_modules_import_with_warning_helpers_available():
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from trueline import comment, decision, writeback; "
                "from trueline.warnings import CatalogWarning, no_ml_lineage; "
                "assert isinstance(no_ml_lineage('urn', 'table'), CatalogWarning)"
            ),
        ],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr

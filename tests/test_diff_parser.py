from pathlib import Path

from trueline.diff_parser import ChangeKind, parse_diff

FIXTURES = Path(__file__).parent / "fixtures"


def test_pr_2847_parses_drop_and_add():
    files = parse_diff((FIXTURES / "pr_2847.diff").read_text(encoding="utf-8"))
    by_path = {f.file_path: f for f in files}
    assert set(by_path) == {
        "demo_repo/models/order_items.sql",
        "demo_repo/models/feature_order_risk.sql",
    }
    order_items = by_path["demo_repo/models/order_items.sql"]
    assert order_items.is_sql
    assert [(c.name, c.kind) for c in order_items.columns] == [("return_date", ChangeKind.DROP)]
    feature = by_path["demo_repo/models/feature_order_risk.sql"]
    assert [(c.name, c.kind) for c in feature.columns] == [
        ("return_date", ChangeKind.DROP),
        ("customer_email", ChangeKind.ADD),
    ]


def test_non_sql_files_ignored():
    files = parse_diff((FIXTURES / "pr_2847.diff").read_text(encoding="utf-8"))
    assert all(f.is_sql for f in files)
    assert not any("unrelated.py" in f.file_path for f in files)


def test_type_change_detected():
    diff = """diff --git a/a.sql b/a.sql
--- a/a.sql
+++ b/a.sql
@@ -1,1 +1,1 @@
-    return_date DATE,
+    return_date TIMESTAMP,
"""
    files = parse_diff(diff)
    assert [(c.name, c.kind) for c in files[0].columns] == [("return_date", ChangeKind.TYPE_CHANGE)]


def test_empty_diff():
    assert parse_diff("") == []
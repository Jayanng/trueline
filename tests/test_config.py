import json
from pathlib import Path

import pytest

from trueline.config import Config, TableRef, load_table_map, parse_dataset_urn


def test_table_ref_urn():
    ref = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
    assert ref.qualified == "ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS"
    assert ref.urn == "urn:li:dataset:(urn:li:dataPlatform:snowflake,ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS,PROD)"


def test_table_ref_empty_schema_no_double_dot():
    ref = TableRef(platform="snowflake", db="order_entry", schema="", table="feature_order_risk")
    assert ref.qualified == "order_entry.feature_order_risk"
    assert ref.urn == (
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,order_entry.feature_order_risk,PROD)"
    )
    assert ".." not in ref.qualified


def test_parse_dataset_urn_roundtrip():
    ref = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
    assert parse_dataset_urn(ref.urn) == ref
    two_part = TableRef(platform="snowflake", db="order_entry", schema="", table="feature_order_risk")
    assert parse_dataset_urn(two_part.urn) == two_part


def test_parse_dataset_urn_rejects_non_dataset():
    with pytest.raises(ValueError):
        parse_dataset_urn("urn:li:mlModel:fraud_model_v4")


def test_load_table_map(tmp_path: Path):
    f = tmp_path / "table_map.json"
    f.write_text(json.dumps({
        "demo_repo/models/order_items.sql": {
            "platform": "snowflake", "db": "ORDER_ENTRY_DB", "schema": "ORDER_ENTRY", "table": "ORDER_ITEMS",
        }
    }), encoding="utf-8")
    m = load_table_map(f)
    assert m["demo_repo/models/order_items.sql"].table == "ORDER_ITEMS"
    assert m["demo_repo/models/order_items.sql"].env == "PROD"


def test_config_defaults(monkeypatch):
    for key in (
        "DATAHUB_GMS_URL",
        "DATAHUB_GMS_TOKEN",
        "MCP_SERVER_URL",
        "GMI_API_KEY",
        "LLM_API_KEY",
        "ANTHROPIC_API_KEY",
        "GMI_MODEL",
        "LLM_MODEL",
        "ANTHROPIC_MODEL",
        "GMI_BASE_URL",
        "LLM_BASE_URL",
        "TRUELINE_DRY_RUN",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = Config()
    assert cfg.gms_url == "http://localhost:8080"
    assert cfg.mcp_url == "http://127.0.0.1:8000/mcp"
    assert cfg.dry_run is True
    assert cfg.has_llm is False
    assert cfg.has_anthropic is False
    assert cfg.llm_base_url == "https://api.gmi-serving.com/v1"
    assert cfg.llm_model == "deepseek-ai/DeepSeek-V4-Flash"


def test_config_gmi_env(monkeypatch):
    monkeypatch.setenv("GMI_API_KEY", "gmi-test-key")
    monkeypatch.setenv("GMI_MODEL", "deepseek-ai/DeepSeek-V4-Flash-0731")
    cfg = Config()
    assert cfg.has_llm is True
    assert cfg.llm_api_key == "gmi-test-key"
    assert cfg.llm_model == "deepseek-ai/DeepSeek-V4-Flash-0731"


def test_config_dry_run_false(monkeypatch):
    monkeypatch.setenv("TRUELINE_DRY_RUN", "false")
    assert Config().dry_run is False

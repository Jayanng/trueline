# Trueline Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Trueline core pipeline — PR diff → DataHub ML-lineage impact → severity verdict → PR comment → post-merge write-back — that runs live against a real local DataHub quickstart, plus the demo repo, seed script, and `datahub-pr-guard` skill, so the three demo moments work end to end.

**Architecture:** A deterministic Python engine (diff parsing, lineage walking, severity, write-back planning/commit) reads and writes a real DataHub Core instance via the Python SDK; an optional Anthropic agent writes prose only, never facts. A `run_local.py` CLI drives the whole pipeline against a git diff (primary demo path); a GitHub Action wraps the same code for self-hosted-runner PRs. `seed/seed_ml_tail.py` grafts the ML tail onto the official `showcase-ecommerce` datapack with real SDK calls (honestly labeled demo entities).

**Tech Stack:** Python 3.11 (≥3.10) · `acryl-datahub` SDK · `sqlglot` · `unidiff` · `anthropic` (async) · `aiosqlite` · `pytest` · Docker Desktop + `datahub` CLI (dev infra only) · git.

## Global Constraints

- **Reality principle (hard rule, from `ARCHITECTURE.md` §4):** every verdict is computed live from the real graph; no hardcoded demo output, no canned comments, no invented metrics (null rates, P95, SLA numbers), no fake social proof. The ML tail is real metadata created via real SDK calls but is *demo data* — the README says so.
- **Dry-run by default.** The pipeline writes nothing unless `--commit` is passed (post-merge only). Pre-merge runs propose; the PR is the approval gate.
- **Engine reads/writes via the Python SDK** (`DataHubClient`). MCP tools are for the agent layer/skill story, not the engine. MCP cannot write lineage — all lineage writes are SDK calls.
- **ML lineage is NOT `add_lineage`:** ML edges use aspect fields (`MLFeaturePropertiesClass(sources=[...])`, `MLModelPropertiesClass(mlFeatures=[...])` read-modify-write). `add_lineage`/`infer_lineage_from_sql` are for Dataset → Dataset only.
- **Terms:** SDK pattern is get → mutate → update (`entity["col"].add_term(urn)` + `client.entities.update(entity)`). There is no `add_terms` SDK helper.
- **Lineage writes use `SYNC_WAIT` emit mode** so before/after verification is honest.
- **Instance:** local quickstart, GMS `http://localhost:8080`, UI `http://localhost:9002` (datahub/datahub). Datapack: `showcase-ecommerce` (~1,065 entities, zero ML entities). Token via UI Settings → Access Tokens; token/key only in `.env` (gitignored), never committed.
- **The demo repo lives inside the trueline repo** (`demo_repo/`); demo branches `main` + `demo/pr-2847` are branches of the trueline repo itself (no nested git repos).
- **Unit tests never touch the network.** A `FakeGateway` (tests/fakes.py) implements the same interface as `DataHubGateway`. The e2e test is gated on `TRUELINE_E2E=1`.
- **SPIKE steps** are marked inline: they verify an API surface against the live instance/docs and pin the exact call in the code before proceeding. Never guess an SDK signature.
- **Commit style:** conventional commits, one per task (`feat:`, `test:`, `chore:`, `docs:`). No commits outside task steps.
- **Apache 2.0:** LICENSE fetched from the official URL (Task 16). Repo must be public at submission.
- **Out of scope for this plan:** the Next.js landing/product app (separate plan, per `DESIGN.md`), demo video, Devpost write-up.

---

### Task 1: Repo scaffold (git init, pyproject, env template, smoke test)

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `trueline/__init__.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: installable package `trueline` (empty), pytest running, git repo root for all later tasks.

- [ ] **Step 1: Initialize the git repo and create the package skeleton**

Run in `C:\Users\dell\Documents\VS_code\trueline`:

```powershell
git init -b main
mkdir trueline, tests
git config user.name "Trueline"   # adjust to your GitHub identity if unset
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "trueline"
version = "0.1.0"
description = "Gate pull requests on DataHub ML lineage; true the graph from the PR's own SQL."
requires-python = ">=3.10"
dependencies = [
    "acryl-datahub>=1.0.0",
    "sqlglot>=25.0.0",
    "unidiff>=0.7.5",
    "anthropic>=0.40.0",
    "aiosqlite>=0.20.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.24.0"]

[tool.setuptools.packages.find]
include = ["trueline*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
.trueline/
dist/
build/
*.egg-info/
node_modules/
.next/
```

- [ ] **Step 4: Write `.env.example`**

```dotenv
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_GMS_TOKEN=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-5
TRUELINE_DRY_RUN=true
TRUELINE_STATE_DB=.trueline/state.db
```

- [ ] **Step 5: Write `trueline/__init__.py` and the smoke test**

`trueline/__init__.py`:

```python
__version__ = "0.1.0"
```

`tests/test_smoke.py`:

```python
import trueline


def test_package_imports():
    assert trueline.__version__ == "0.1.0"
```

- [ ] **Step 6: Install dev deps and run the test**

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example trueline tests
git commit -m "chore: scaffold trueline package, env template, pytest"
```

---

### Task 2: Batch 0 — local DataHub quickstart, datapack, PAT

**Files:**
- Create: `.env` (gitignored — PAT lives here only)
- Create: `seed/discover_graph.py` (first version)

**Interfaces:**
- Consumes: Task 1 scaffold.
- Produces: running instance (GMS :8080, UI :9002), `showcase-ecommerce` loaded, `DATAHUB_GMS_TOKEN` in `.env`, and the discovery script that Task 8 grows into `verify_graph.py`.

> Docker Desktop is installed per-user at `C:\Users\dell\AppData\Local\Programs\DockerDesktop\` (launcher `Docker Desktop.exe`), but the daemon was not running at plan time.

- [ ] **Step 1: Start Docker Desktop and wait for the engine**

```powershell
Start-Process "C:\Users\dell\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
docker info --format "{{.ServerVersion}}"   # retry until it prints a version (can take 60-120s)
```

Expected: `docker info` succeeds.

- [ ] **Step 2: Install the DataHub CLI**

```powershell
python -m pip install --upgrade acryl-datahub
datahub version
```

- [ ] **Step 3: Start the quickstart**

```powershell
datahub docker quickstart
```

Expected: prints the status of ~14 containers and "DataHub is now running". First run downloads images (can take several minutes — allow up to 30 min).

- [ ] **Step 4: Verify the UI and GMS**

```powershell
(Invoke-WebRequest -UseBasicParsing http://localhost:9002).StatusCode   # expect 200
(Invoke-WebRequest -UseBasicParsing http://localhost:8080/health).Content  # expect {"isHealthy":true}
```

- [ ] **Step 5: Log in to the UI and mint a Personal Access Token (user action)**

Browser → `http://localhost:9002` → log in `datahub` / `datahub` → Settings (top-right avatar) → Access Tokens → **Create new token** (name `trueline-dev`) → copy the token. It is shown once.

- [ ] **Step 6: Write the token to `.env` and load the datapack**

```powershell
# .env content: copy .env.example and set DATAHUB_GMS_TOKEN=<token from Step 5>
$env:DATAHUB_GMS_URL="http://localhost:8080"
$env:DATAHUB_GMS_TOKEN="<token>"
datahub datapack load showcase-ecommerce
```

Expected: prints "Loading datapack showcase-ecommerce" and completes without error. (The `datapack` command is officially marked experimental — expected.)

- [ ] **Step 7: Write the discovery script `seed/discover_graph.py`**

```python
"""Print ground-truth facts about the seeded instance. Grown into verify_graph.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.sdk import DataHubClient

load_dotenv()


def main() -> None:
    client = DataHubClient(server=os.environ["DATAHUB_GMS_URL"], token=os.environ["DATAHUB_GMS_TOKEN"])
    # SPIKE: pin the exact search API (client.entities.search vs client.search) and
    # the total_count attribute by running this against the live instance.
    print("search: SPIKE - pin signature and count")
    for query in ["order_items", "feature_order_risk", "mlModel", "customers"]:
        try:
            results = client.entities.search(query=query, entity_type="dataset")
            print(f"  {query}: {[str(r.urn) for r in results][:5]}")
        except Exception as exc:  # noqa: BLE001 - SPIKE prints, does not hide
            print(f"  {query}: ERROR {exc!r}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run discovery and pin the ground truth**

```powershell
python seed/discover_graph.py
```

Expected: prints real URNs. From the output, pin into this plan's later tasks the exact dataset URN shapes for `order_items`, `customers` (case! e.g. `ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS` vs `order_entry.order_items`) and confirm `feature_order_risk` returns nothing. Record the exact case here before Task 8:

```
Pinned names: ____________________________________________________________________
```

- [ ] **Step 9: Commit**

```bash
git add seed/discover_graph.py .env.example
git commit -m "chore: add graph discovery script (Batch 0 quickstart verification)"
```

---

### Task 3: config.py — env config, TableRef, table map

**Files:**
- Create: `trueline/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Config` (frozen dataclass): fields `gms_url`, `gms_token`, `anthropic_api_key`, `anthropic_model`, `dry_run: bool`, `state_db: Path`; property `has_anthropic: bool`.
  - `TableRef` (frozen dataclass): fields `platform`, `db`, `schema`, `table`, `env: str = "PROD"`; properties `qualified: str` and `urn: str`.
  - `load_table_map(path: Path) -> dict[str, TableRef]` — repo-relative file path → TableRef, from JSON.
  - `parse_dataset_urn(urn: str) -> TableRef` — reverse of `TableRef.urn`.

- [ ] **Step 1: Write the failing tests `tests/test_config.py`**

```python
import json
from pathlib import Path

import pytest

from trueline.config import Config, TableRef, load_table_map, parse_dataset_urn


def test_table_ref_urn():
    ref = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
    assert ref.qualified == "ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS"
    assert ref.urn == "urn:li:dataset:(urn:li:dataPlatform:snowflake,ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS,PROD)"


def test_parse_dataset_urn_roundtrip():
    ref = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
    assert parse_dataset_urn(ref.urn) == ref


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
    for key in ("DATAHUB_GMS_URL", "DATAHUB_GMS_TOKEN", "ANTHROPIC_API_KEY", "TRUELINE_DRY_RUN"):
        monkeypatch.delenv(key, raising=False)
    cfg = Config()
    assert cfg.gms_url == "http://localhost:8080"
    assert cfg.dry_run is True
    assert cfg.has_anthropic is False


def test_config_dry_run_false(monkeypatch):
    monkeypatch.setenv("TRUELINE_DRY_RUN", "false")
    assert Config().dry_run is False
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_config.py -v
```

- [ ] **Step 3: Write `trueline/config.py`**

```python
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_DATASET_URN = re.compile(
    r"^urn:li:dataset:\(urn:li:dataPlatform:([^,()]+),([^,()]+),(PROD|DEV|TEST|STAGING)\)$"
)


@dataclass(frozen=True)
class TableRef:
    platform: str
    db: str
    schema: str
    table: str
    env: str = "PROD"

    @property
    def qualified(self) -> str:
        return f"{self.db}.{self.schema}.{self.table}"

    @property
    def urn(self) -> str:
        return f"urn:li:dataset:(urn:li:dataPlatform:{self.platform},{self.qualified},{self.env})"


def parse_dataset_urn(urn: str) -> TableRef:
    match = _DATASET_URN.match(urn)
    if not match:
        raise ValueError(f"not a dataset urn: {urn}")
    platform, qualified, env = match.groups()
    parts = qualified.split(".")
    if len(parts) == 3:
        db, schema, table = parts
    else:
        db, schema, table = "", "", qualified
    return TableRef(platform=platform, db=db, schema=schema, table=table, env=env)


@dataclass(frozen=True)
class Config:
    gms_url: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_URL", "http://localhost:8080"))
    gms_token: str = field(default_factory=lambda: os.getenv("DATAHUB_GMS_TOKEN", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
    dry_run: bool = field(
        default_factory=lambda: os.getenv("TRUELINE_DRY_RUN", "true").lower() in ("1", "true", "yes")
    )
    state_db: Path = field(default_factory=lambda: Path(os.getenv("TRUELINE_STATE_DB", ".trueline/state.db")))

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)


def load_table_map(path: Path) -> dict[str, TableRef]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, TableRef] = {}
    for key, value in data.items():
        out[key] = TableRef(
            platform=value["platform"],
            db=value["db"],
            schema=value["schema"],
            table=value["table"],
            env=value.get("env", "PROD"),
        )
    return out
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add trueline/config.py tests/test_config.py
git commit -m "feat: config, TableRef, table map, dataset URN parsing"
```

---

### Task 4: diff_parser.py — PR diff → changed columns

**Files:**
- Create: `trueline/diff_parser.py`
- Create: `tests/fixtures/pr_2847.diff`
- Create: `tests/test_diff_parser.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ChangeKind(str, Enum)`: `DROP`, `ADD`, `TYPE_CHANGE`.
  - `ChangedColumn`: fields `name: str`, `kind: ChangeKind`.
  - `ChangedFile`: fields `file_path: str`, `columns: tuple[ChangedColumn, ...]`, `is_sql: bool`.
  - `parse_diff(diff_text: str) -> list[ChangedFile]` — pure, no disk I/O.

- [ ] **Step 1: Write the fixture diff `tests/fixtures/pr_2847.diff`**

This is the static snapshot of the demo PR (same content Task 14's branch produces — keep them in sync).

```diff
diff --git a/demo_repo/models/order_items.sql b/demo_repo/models/order_items.sql
--- a/demo_repo/models/order_items.sql
+++ b/demo_repo/models/order_items.sql
@@ -3,10 +3,9 @@
     order_id,
     customer_id,
     product_id,
     order_date,
-    return_date,
     order_total
 from {{ ref('orders') }}
diff --git a/demo_repo/models/feature_order_risk.sql b/demo_repo/models/feature_order_risk.sql
--- a/demo_repo/models/feature_order_risk.sql
+++ b/demo_repo/models/feature_order_risk.sql
@@ -1,9 +1,10 @@
 select
    order_id,
    customer_id,
-    return_date,
+    customers.cust_email as customer_email,
    order_total,
     case when order_total > 500 then 0.4 else 0.1 end as risk_score
 from {{ ref('order_items') }}
+left join {{ ref('customers') }} on customers.customer_id = order_items.customer_id
diff --git a/demo_repo/models/unrelated.py b/demo_repo/models/unrelated.py
--- a/demo_repo/models/unrelated.py
+++ b/demo_repo/models/unrelated.py
@@ -1,2 +1,2 @@
-x = 1
+x = 2
```

- [ ] **Step 2: Write the failing tests `tests/test_diff_parser.py`**

```python
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
@@ -1,2 +1,2 @@
-    return_date DATE,
+    return_date TIMESTAMP,
"""
    files = parse_diff(diff)
    assert [(c.name, c.kind) for c in files[0].columns] == [("return_date", ChangeKind.TYPE_CHANGE)]


def test_empty_diff():
    assert parse_diff("") == []
```

- [ ] **Step 3: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_diff_parser.py -v
```

- [ ] **Step 4: Write `trueline/diff_parser.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from unidiff import PatchSet


class ChangeKind(str, Enum):
    DROP = "DROP"
    ADD = "ADD"
    TYPE_CHANGE = "TYPE_CHANGE"


@dataclass(frozen=True)
class ChangedColumn:
    name: str
    kind: ChangeKind


@dataclass(frozen=True)
class ChangedFile:
    file_path: str
    columns: tuple[ChangedColumn, ...]
    is_sql: bool = False


_SKIP = frozenset(
    {
        "select", "from", "where", "join", "left", "right", "inner", "outer", "full",
        "on", "and", "or", "as", "by", "group", "order", "having", "limit", "offset",
        "create", "table", "alter", "drop", "column", "add", "modify", "change", "if",
        "not", "exists", "primary", "key", "foreign", "references", "constraint",
        "unique", "index", "with", "union", "all", "distinct", "case", "when", "then",
        "else", "end", "values", "into", "insert", "update", "delete", "set", "null",
        "default", "comment", "partition", "using", "external", "overwrite", "merge",
        "count", "sum", "avg", "min", "max", "cast", "coalesce", "row_number", "rank",
        "over", "partitioned", "clustered", "sorted", "properties", "tblproperties",
        "stored", "location", "format", "engine", "charset", "returns", "return",
    }
)

_IDENT = re.compile(r"^[+-]\s*([A-Za-z_][A-Za-z0-9_]*)\b(.*)$")
_TOKENS = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _words(line: str) -> list[str]:
    return _TOKENS.findall(line)


def _classify(removed: list[str], added: list[str]) -> list[ChangedColumn]:
    changes: list[ChangedColumn] = []
    removed_map = {m.group(1): m for m in (_IDENT.match(l) for l in removed) if m}
    added_map = {m.group(1): m for m in (_IDENT.match(l) for l in added) if m}
    for name in sorted(set(removed_map) - set(added_map)):
        changes.append(ChangedColumn(name=name, kind=ChangeKind.DROP))
    for name in sorted(set(added_map) - set(removed_map)):
        changes.append(ChangedColumn(name=name, kind=ChangeKind.ADD))
    for name in sorted(set(removed_map) & set(added_map)):
        if name.lower() in _SKIP:
            continue
        removed_words = _words(removed_map[name].group(2))
        added_words = _words(added_map[name].group(2))
        if removed_words and added_words and removed_words != added_words:
            changes.append(ChangedColumn(name=name, kind=ChangeKind.TYPE_CHANGE))
    return changes


def parse_diff(diff_text: str) -> list[ChangedFile]:
    files: list[ChangedFile] = []
    for patched in PatchSet(diff_text):
        if not patched.is_modified_file or not patched.path.endswith(".sql"):
            continue
        removed: list[str] = []
        added: list[str] = []
        for hunk in patched:
            for line in hunk:
                if line.is_removed:
                    removed.append(line.value.rstrip("\n"))
                elif line.is_added:
                    added.append(line.value.rstrip("\n"))
        columns = tuple(c for c in _classify(removed, added) if c.name.lower() not in _SKIP)
        files.append(ChangedFile(file_path=patched.path, columns=columns, is_sql=True))
    return files
```

- [ ] **Step 5: Run tests — expect PASS**

```powershell
python -m pytest tests/test_diff_parser.py -v
```

- [ ] **Step 6: Commit**

```bash
git add trueline/diff_parser.py tests/fixtures/pr_2847.diff tests/test_diff_parser.py
git commit -m "feat: diff parser (unidiff + column change classification)"
```

---

### Task 5: datahub_client.py — SDK gateway (reads + lineage writes)

**Files:**
- Create: `trueline/datahub_client.py`
- Create: `tests/fakes.py`
- Create: `tests/test_gateway_contract.py`

**Interfaces:**
- Consumes: `Config`, `TableRef` (Task 3).
- Produces (the gateway contract every other task depends on):
  - `LineageResult` (frozen dataclass): `urn`, `entity_type`, `platform`, `name`, `hops: int`, `paths: tuple[tuple[str, ...], ...]`.
  - `DataHubGateway`:
    - `downstream(ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]`
    - `entity(urn: str) -> dict` (SDK entity dict)
    - `owners(urn: str) -> list[str]`
    - `environment(urn: str) -> str` ("" if unknown)
    - `search(query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]` (URNs)
    - `column_terms(ref: TableRef, column: str) -> list[str]` (term URNs)
    - `add_lineage(upstream: TableRef, downstream: TableRef, column_lineage: dict[str, list[str]] | None = None, wait: bool = False) -> None`
    - `add_term(ref: TableRef, column: str, term_urn: str) -> None`
  - `tests/fakes.py`: `FakeGateway` implementing the same contract in memory (records `add_lineage`/`add_term` calls; seeds fixtures).

- [ ] **Step 1: Write the contract test `tests/test_gateway_contract.py`** (both implementations must satisfy it)

```python
import pytest

from trueline.config import TableRef
from tests.fakes import FakeGateway, LINEAGE, TERMS

UP = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
DOWN = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="FEATURE_ORDER_RISK")


@pytest.fixture
def gateway():
    return FakeGateway(seed=LINEAGE, terms=TERMS)


def test_downstream_returns_results(gateway: FakeGateway):
    results = gateway.downstream(UP, max_hops=4)
    assert any(r.urn == "urn:li:mlModel:fraud_model_v4" for r in results)


def test_downstream_column_filter(gateway: FakeGateway):
    assert gateway.downstream(UP, column="return_date", max_hops=1) == []


def test_owners_and_environment(gateway: FakeGateway):
    assert gateway.owners("urn:li:mlModel:fraud_model_v4") == ["riya"]
    assert gateway.environment("urn:li:mlModel:fraud_model_v4") == "PROD"
    assert gateway.environment("urn:li:dataset:(urn:li:dataPlatform:looker,foo,PROD)") == ""


def test_column_terms(gateway: FakeGateway):
    cust = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="CUSTOMERS")
    assert any("pii" in t.lower() for t in gateway.column_terms(cust, "cust_email"))


def test_add_lineage_records(gateway: FakeGateway):
    gateway.add_lineage(UP, DOWN, column_lineage={"risk_score": ["return_date"]}, wait=True)
    assert ("LINEAGE", UP.urn, DOWN.urn, {"risk_score": ["return_date"]}) in gateway.writes


def test_add_term_records(gateway: FakeGateway):
    gateway.add_term(DOWN, "customer_email", "urn:li:glossaryTerm:pii.email")
    assert ("TERM", DOWN.urn, "customer_email", "urn:li:glossaryTerm:pii.email") in gateway.writes
```

- [ ] **Step 2: Write `tests/fakes.py`** (the seed mirrors the real graph after Task 8: dataset → MLFeature → MLModel → MLModelGroup)

```python
from __future__ import annotations

from dataclasses import dataclass, field

from trueline.config import TableRef
from trueline.datahub_client import LineageResult

ORDER_ITEMS = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="ORDER_ITEMS")
FEATURE = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="FEATURE_ORDER_RISK")
CUSTOMERS = TableRef(platform="snowflake", db="ORDER_ENTRY_DB", schema="ORDER_ENTRY", table="CUSTOMERS")

ML_FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
ML_MODEL_URN = "urn:li:mlModel:fraud_model_v4"
ML_GROUP_URN = "urn:li:mlModelGroup:fraud-scoring"

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
    ],
    FEATURE.urn: [LineageResult(urn=ML_FEATURE_URN, entity_type="mlfeature", platform="mlflow",
                                name="feature_order_risk", hops=1, paths=((FEATURE.urn, ML_FEATURE_URN),))],
}

TERMS = {
    (CUSTOMERS.urn, "cust_email"): ["urn:li:glossaryTerm:OrderEntry.PII"],
}

OWNERS = {ML_MODEL_URN: ["riya"]}
ENVS = {ML_MODEL_URN: "PROD"}


@dataclass
class FakeGateway:
    seed: dict[str, list[LineageResult]] = field(default_factory=lambda: LINEAGE)
    terms: dict[tuple[str, str], list[str]] = field(default_factory=lambda: TERMS)
    writes: list[tuple] = field(default_factory=list)

    def downstream(self, ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]:
        results = [r for r in self.seed.get(ref.urn, []) if r.hops <= max_hops]
        if column is not None:
            # Seed has table-level lineage only (the deliberate gap): column-filtered
            # traversal finds nothing until a write-back adds column lineage.
            return []
        return results

    def entity(self, urn: str) -> dict:
        return {"urn": urn}

    def owners(self, urn: str) -> list[str]:
        return OWNERS.get(urn, [])

    def environment(self, urn: str) -> str:
        return ENVS.get(urn, "")

    def search(self, query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]:
        return [urn for urn in self.seed if query.lower() in urn.lower()][:limit]

    def column_terms(self, ref: TableRef, column: str) -> list[str]:
        return self.terms.get((ref.urn, column), [])

    def add_lineage(self, upstream: TableRef, downstream: TableRef,
                    column_lineage: dict[str, list[str]] | None = None, wait: bool = False) -> None:
        self.writes.append(("LINEAGE", upstream.urn, downstream.urn, column_lineage))

    def add_term(self, ref: TableRef, column: str, term_urn: str) -> None:
        self.writes.append(("TERM", ref.urn, column, term_urn))
```

- [ ] **Step 3: Run tests — expect FAIL (no trueline.datahub_client yet)**

```powershell
python -m pytest tests/test_gateway_contract.py -v
```

- [ ] **Step 4: Write `trueline/datahub_client.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from datahub.metadata.urns import DatasetUrn, GlossaryTermUrn
from datahub.sdk import DataHubClient

from .config import Config, TableRef


@dataclass(frozen=True)
class LineageResult:
    urn: str
    entity_type: str
    platform: str
    name: str
    hops: int
    paths: tuple[tuple[str, ...], ...] = ()


class DataHubGateway:
    """Reads/writes the real DataHub graph via the Python SDK.

    The engine (deterministic layer) always uses this class — never the LLM.
    MCP tools belong to the agent layer and the skill; the gateway is SDK-only.
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = DataHubClient(server=cfg.gms_url, token=cfg.gms_token)

    def downstream(self, ref: TableRef, column: str | None = None, max_hops: int = 4) -> list[LineageResult]:
        results = self._client.lineage.get_lineage(
            source_urn=DatasetUrn.from_string(ref.urn),
            source_column=column,
            direction="downstream",
            max_hops=max_hops,
        )
        out: list[LineageResult] = []
        for r in results:
            # SPIKE: verify the exact attribute names of the SDK LineageResult
            # (urn/type/hops/platform/name/paths) and the shape of paths against
            # the live instance before proceeding.
            paths = tuple(tuple(str(x) for x in path) for path in (r.paths or []))
            out.append(
                LineageResult(
                    urn=str(r.urn),
                    entity_type=str(r.type),
                    platform=str(r.platform),
                    name=str(r.name),
                    hops=int(r.hops or 0),
                    paths=paths,
                )
            )
        return out

    def entity(self, urn: str) -> dict:
        return self._client.entities.get(urn)

    def owners(self, urn: str) -> list[str]:
        ent = self.entity(urn)
        getter = getattr(ent, "get_owners", None)
        if getter is None:
            return []
        # SPIKE: pin the return shape (dict[owner_urn, OwnerClass] vs list).
        owners = getter()
        if isinstance(owners, dict):
            return sorted(str(k) for k in owners)
        return [str(o) for o in (owners or [])]

    def environment(self, urn: str) -> str:
        ent = self.entity(urn)
        props = getattr(ent, "custom_properties", None) or {}
        return str(props.get("environment", ""))  # SPIKE: pin how customProperties surfaces on the entity

    def search(self, query: str, entity_type: str = "dataset", limit: int = 20) -> list[str]:
        # SPIKE: pin the SDK search call + result iteration (search vs entities.search).
        results = self._client.entities.search(query=query, entity_type=entity_type, count=limit)
        return [str(r.urn) for r in results]

    def column_terms(self, ref: TableRef, column: str) -> list[str]:
        ent = self.entity(ref.urn)
        col = ent.get(column)
        if col is None:
            return []
        getter = getattr(col, "get_glossary_terms", None)
        if getter is None:
            return []
        terms = getter()
        return [str(t) for t in (terms or [])]  # SPIKE: pin per-column term access

    def add_lineage(self, upstream: TableRef, downstream: TableRef,
                    column_lineage: dict[str, list[str]] | None = None, wait: bool = False) -> None:
        self._client.lineage.add_lineage(
            upstream=DatasetUrn.from_string(upstream.urn),
            downstream=DatasetUrn.from_string(downstream.urn),
            column_lineage=column_lineage,
            emit_mode="SYNC_WAIT" if wait else "SYNC_PRIMARY",
        )

    def add_term(self, ref: TableRef, column: str, term_urn: str) -> None:
        ent = self.entity(ref.urn)
        ent[column].add_term(GlossaryTermUrn.from_string(term_urn))
        self._client.entities.update(ent)
```

- [ ] **Step 5: Run tests — expect PASS**

```powershell
python -m pytest tests/test_gateway_contract.py tests/test_config.py -v
```

- [ ] **Step 6: SPIKE — verify the SDK calls against the live instance**

Write `seed/sdk_spike.py` (throwaway, run, then delete) exercising `downstream`, `owners`, `environment`, `column_terms`, `search` against the real quickstart (Task 2's `order_items` URN). Fix the SPIKE-marked lines to the real shapes. Run:

```powershell
python seed/sdk_spike.py
```

Expected: prints real lineage results from the datapack (e.g. dbt→snowflake hops for order_items). Delete `seed/sdk_spike.py` after pinning.

- [ ] **Step 7: Commit**

```bash
git add trueline/datahub_client.py tests/fakes.py tests/test_gateway_contract.py
git commit -m "feat: SDK gateway for lineage reads and writes (with fake for tests)"
```

---

### Task 6: ml_impact.py — ML entity detection in downstream paths

**Files:**
- Create: `trueline/ml_impact.py`
- Create: `tests/test_ml_impact.py`

**Interfaces:**
- Consumes: `LineageResult` (Task 5).
- Produces:
  - `ml_kind(urn: str) -> str | None` — `MLMODEL`/`MLFEATURE`/`MLMODELGROUP`/`MLFEATURETABLE`/`MLPRIMARYKEY`/`MLMODELDEPLOYMENT` from URN prefix.
  - `MLImpact` (frozen dataclass): `name`, `urn`, `kind`, `env: str`, `owner: str | None`, `path: tuple[str, ...]`; method `display() -> str`.
  - `find_ml_impacts(results: list[LineageResult], owners_by_urn: dict[str, list[str]], env_by_urn: dict[str, str]) -> list[MLImpact]` — dedupes by URN, keeps the shortest path, earliest hops.

- [ ] **Step 1: Write the failing tests `tests/test_ml_impact.py`**

```python
from trueline.datahub_client import LineageResult
from trueline.ml_impact import MLImpact, find_ml_impacts, ml_kind

MODEL = "urn:li:mlModel:fraud_model_v4"
FEATURE = "urn:li:mlFeature:(order_entry,feature_order_risk)"
GROUP = "urn:li:mlModelGroup:fraud-scoring"
DATASET = "urn:li:dataset:(urn:li:dataPlatform:snowflake,ORDER_ENTRY_DB.ORDER_ENTRY.ORDER_ITEMS,PROD)"


def test_ml_kind_by_urn_prefix():
    assert ml_kind(MODEL) == "MLMODEL"
    assert ml_kind(FEATURE) == "MLFEATURE"
    assert ml_kind(GROUP) == "MLMODELGROUP"
    assert ml_kind(DATASET) is None


def test_find_ml_impacts_orders_by_hops_and_dedupes():
    results = [
        LineageResult(urn=MODEL, entity_type="mlmodel", platform="mlflow", name="fraud_model_v4", hops=3),
        LineageResult(urn=MODEL, entity_type="mlmodel", platform="mlflow", name="fraud_model_v4", hops=5),
        LineageResult(urn=DATASET, entity_type="dataset", platform="snowflake", name="ORDER_ITEMS", hops=1),
    ]
    impacts = find_ml_impacts(results, {MODEL: ["riya"]}, {MODEL: "PROD"})
    assert [i.urn for i in impacts] == [MODEL]
    assert impacts[0].owner == "riya"
    assert impacts[0].env == "PROD"
    assert impacts[0].display() == "fraud_model_v4 [MLMODEL] [PROD] owner: @riya"


def test_no_ml_no_impacts():
    results = [LineageResult(urn=DATASET, entity_type="dataset", platform="snowflake", name="ORDER_ITEMS", hops=1)]
    assert find_ml_impacts(results, {}, {}) == []
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_ml_impact.py -v
```

- [ ] **Step 3: Write `trueline/ml_impact.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from .datahub_client import LineageResult

_ML_PREFIXES = {
    "urn:li:mlModel:": "MLMODEL",
    "urn:li:mlFeature:": "MLFEATURE",
    "urn:li:mlFeatureTable:": "MLFEATURETABLE",
    "urn:li:mlPrimaryKey:": "MLPRIMARYKEY",
    "urn:li:mlModelGroup:": "MLMODELGROUP",
    "urn:li:mlModelDeployment:": "MLMODELDEPLOYMENT",
}


def ml_kind(urn: str) -> str | None:
    for prefix, kind in _ML_PREFIXES.items():
        if urn.startswith(prefix):
            return kind
    return None


@dataclass(frozen=True)
class MLImpact:
    name: str
    urn: str
    kind: str
    env: str = ""
    owner: str | None = None
    path: tuple[str, ...] = ()

    def display(self) -> str:
        bits = [self.name, f"[{self.kind}]"]
        if self.env:
            bits.append(f"[{self.env}]")
        if self.owner:
            bits.append(f"owner: @{self.owner}")
        return " ".join(bits)


def find_ml_impacts(
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> list[MLImpact]:
    by_urn: dict[str, LineageResult] = {}
    for r in sorted(results, key=lambda r: (r.hops, len(r.paths) if r.paths else 0)):
        kind = ml_kind(r.urn)
        if kind is None:
            continue
        by_urn.setdefault(r.urn, r)
    out: list[MLImpact] = []
    for urn, r in by_urn.items():
        owners = owners_by_urn.get(urn, [])
        out.append(
            MLImpact(
                name=r.name,
                urn=urn,
                kind=ml_kind(urn) or "",
                env=env_by_urn.get(urn, ""),
                owner=owners[0] if owners else None,
                path=r.paths[0] if r.paths else (urn,),
            )
        )
    return out
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_ml_impact.py -v
```

- [ ] **Step 5: Commit**

```bash
git add trueline/ml_impact.py tests/test_ml_impact.py
git commit -m "feat: ML entity detection in downstream lineage paths"
```

---

### Task 7: impact.py — deterministic ML-first severity engine

**Files:**
- Create: `trueline/impact.py`
- Create: `tests/test_impact.py`

**Interfaces:**
- Consumes: `TableRef`, `LineageResult`/`DataHubGateway` contract, `ChangedFile`/`ChangedColumn`, `find_ml_impacts` (Tasks 3–6).
- Produces:
  - `DASHBOARD_PLATFORMS: frozenset[str]` = `{"looker", "tableau", "powerbi", "superset"}`.
  - `AffectedEntity` (frozen dataclass): `urn`, `name`, `kind`, `owner: str | None`, `reason: str`.
  - `TableVerdict` (frozen dataclass): `ref: TableRef`, `file_path: str`, `columns: tuple[ChangedColumn, ...]`, `severity: str`, `affected: tuple[AffectedEntity, ...]`, `message: str`.
  - `compute_verdict(ref, file: ChangedFile, results: list[LineageResult], owners_by_urn: dict[str, list[str]], env_by_urn: dict[str, str]) -> TableVerdict`.
- **Severity rules (verbatim from `DESIGN.md` §3.3):** `CRITICAL` = reaches a prod ML model/ML entity downstream · `HIGH` = dashboards/BI consumers · `MEDIUM` = multiple downstream consumers (or any non-additive change) · `LOW` = additive change only.

- [ ] **Step 1: Write the failing tests `tests/test_impact.py`**

```python
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_impact.py -v
```

- [ ] **Step 3: Write `trueline/impact.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from .config import TableRef
from .datahub_client import LineageResult
from .diff_parser import ChangeKind, ChangedColumn, ChangedFile
from .ml_impact import find_ml_impacts

DASHBOARD_PLATFORMS = frozenset({"looker", "tableau", "powerbi", "superset"})


@dataclass(frozen=True)
class AffectedEntity:
    urn: str
    name: str
    kind: str
    owner: str | None
    reason: str


@dataclass(frozen=True)
class TableVerdict:
    ref: TableRef
    file_path: str
    columns: tuple[ChangedColumn, ...]
    severity: str
    affected: tuple[AffectedEntity, ...]
    message: str


def compute_verdict(
    ref: TableRef,
    file: ChangedFile,
    results: list[LineageResult],
    owners_by_urn: dict[str, list[str]],
    env_by_urn: dict[str, str],
) -> TableVerdict:
    ml = find_ml_impacts(results, owners_by_urn, env_by_urn)
    if ml:
        affected = tuple(
            AffectedEntity(i.urn, i.name, i.kind, i.owner, "downstream ML entity") for i in ml
        )
        return TableVerdict(
            ref, file.file_path, file.columns, "CRITICAL", affected,
            "silent prod-model breakage — downstream ML entity",
        )
    dashboards = [r for r in results if r.platform.lower() in DASHBOARD_PLATFORMS]
    if dashboards:
        affected = tuple(
            AffectedEntity(r.urn, r.name, "DASHBOARD", None, "downstream BI consumer") for r in dashboards
        )
        return TableVerdict(ref, file.file_path, file.columns, "HIGH", affected, "downstream dashboards/BI consumers")
    if len(results) > 1:
        affected = tuple(
            AffectedEntity(r.urn, r.name, r.entity_type.upper() or "DATASET", None, "downstream")
            for r in results
        )
        return TableVerdict(ref, file.file_path, file.columns, "MEDIUM", affected, "multiple downstream consumers")
    if all(c.kind == ChangeKind.ADD for c in file.columns):
        return TableVerdict(ref, file.file_path, file.columns, "LOW", (), "additive change only")
    return TableVerdict(ref, file.file_path, file.columns, "MEDIUM", (), "non-additive change, no ML/dashboard consumers")
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_impact.py -v
```

- [ ] **Step 5: Commit**

```bash
git add trueline/impact.py tests/test_impact.py
git commit -m "feat: deterministic ML-first severity engine"
```

---

### Task 8: seed_ml_tail.py + verify_graph.py — graft the ML tail (real SDK writes)

**Files:**
- Create: `seed/seed_ml_tail.py`
- Create: `seed/verify_graph.py` (replaces/grows `seed/discover_graph.py` — delete the latter)
- Create: `seed/props.yaml` (structured property definition)
- Create: `seed/recipes/feature_order_risk.yaml` (file-based ingestion recipe for the dataset)
- Create: `seed/README.md` (honesty note)

**Interfaces:**
- Consumes: `Config`/`TableRef` (Task 3), live instance (Task 2).
- Produces in the real graph (all via real SDK/CLI calls, honestly labeled demo entities):
  - Dataset `FEATURE_ORDER_RISK` (snowflake, `order_entry.feature_order_risk`) with schema + **table-level only** lineage from `order_items` (the deliberate column-lineage gap), source `seed/recipes/feature_order_risk.yaml`.
  - MLFeature `feature_order_risk` (`MLFeaturePropertiesClass(sources=[feature dataset])`).
  - MLModel `fraud_model_v4` (`MLModelPropertiesClass(mlFeatures=[feature])`, owner `@riya`, customProperties `environment=PROD`).
  - MLModelGroup `fraud-scoring` referencing the model.
  - Structured property `trueline.reviewed`.
  - `seed/verify_graph.py`: prints ground-truth facts (dataset count, ML entities, downstream path from `FEATURE_ORDER_RISK` → feature → model → group, owners, cust_email PII status) and fails nonzero on any mismatch; writes the pinned `demo_repo/table_map.json` (Task 14's file, created here).

> **SPIKE gates in this task:** (a) ML entity creation call shape — prefer `datahub.sdk` entity classes (`MLModel(...)`, `.as_mcps()`) or `MetadataChangeProposalWrapper` + `DatahubRestEmitter`; (b) `CorpUser` — use an existing user if present (e.g. `datahub`), else create `riya` via `CorpUserInfoClass` MCP; (c) `datahub properties upsert -f` YAML schema (fallback: GraphQL `createStructuredProperty`); (d) whether `get_lineage` traverses ML edges — if not, manually walk `MLFeatureProperties.sources` and `MLModelProperties.mlFeatures`.

- [ ] **Step 1: Write `seed/recipes/feature_order_risk.yaml`**

```yaml
source:
  type: file
  config:
    path: seed/recipes/feature_order_risk.csv
    parser: csv
sink:
  type: datahub-rest
  config:
    server: ${DATAHUB_GMS_URL}
    token: ${DATAHUB_GMS_TOKEN}
```

- [ ] **Step 2: Write `seed/recipes/feature_order_risk.csv`**

```csv
order_id,customer_id,customer_email,order_total,risk_score
10001,51,alice@example.com,1299.00,0.4
10002,52,bob@example.com,220.50,0.1
10003,53,carol@example.com,87.90,0.1
10004,54,dave@example.com,612.00,0.4
10005,55,erin@example.com,340.00,0.1
```

- [ ] **Step 3: Ingest the dataset (creates the real dataset + schema)**

```powershell
$env:DATAHUB_GMS_URL="http://localhost:8080"
$env:DATAHUB_GMS_TOKEN="<token>"
datahub ingest -c seed/recipes/feature_order_risk.yaml
```

Expected: creates the dataset (SPIKE: confirm the produced URN in the UI — search "FEATURE_ORDER_RISK"; pin its exact name case here: `_____________`).

- [ ] **Step 4: Write `seed/seed_ml_tail.py`** (idempotent — safe to re-run after `datahub datapack unload/reload`)

```python
"""Graft the demo ML tail onto the showcase-ecommerce datapack.

These are DEMO entities — real DataHub metadata written via real SDK calls,
created because the official datapack ships zero ML entities. Honest labeling
lives in seed/README.md and the project README.

Idempotent: checks existence before emitting; re-running is safe.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter

load_dotenv()

GMS_URL = os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
GMS_TOKEN = os.getenv("DATAHUB_GMS_TOKEN", "")

FEATURE_DATASET = make_dataset_urn(platform="snowflake", name="order_entry.feature_order_risk", env="PROD")
ORDER_ITEMS = make_dataset_urn(platform="snowflake", name="order_entry.order_items", env="PROD")
ML_FEATURE_URN = "urn:li:mlFeature:(order_entry,feature_order_risk)"
ML_MODEL_URN = "urn:li:mlModel:fraud_model_v4"
ML_GROUP_URN = "urn:li:mlModelGroup:fraud-scoring"
OWNER = "urn:li:corpuser:riya"  # SPIKE: use an existing corpuser if riya is not created


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=GMS_TOKEN)

    # 1) Dataset -> MLFeature: feature sources point at the dataset (creates the edge).
    #    SPIKE: pin the exact MCP constructor fields below against the SDK/docs.
    from datahub.metadata.schema_classes import MLFeaturePropertiesClass

    feature_props = MLFeaturePropertiesClass(
        description="Fraud risk score feature; downstream of order_items (demo tail).",
        dataType="DOUBLE",
        featureNamespace="order_entry",
        sources=[FEATURE_DATASET],  # SPIKE: sources take dataset urn strings/urns
    )
    emitter.emit_mcp("mlFeature", ML_FEATURE_URN, "mlFeatureProperties", feature_props)
    print(f"seeded MLFeature {ML_FEATURE_URN}")

    # 2) MLModel with feature + owner + env (read-modify-write pattern).
    from datahub.metadata.schema_classes import MLModelPropertiesClass, OwnerClass, OwnershipClass, OwnershipTypeClass

    model_props = MLModelPropertiesClass(
        description="Production fraud model (demo tail).",
        mlFeatures=[ML_FEATURE_URN],
        customProperties={"environment": "PROD"},
    )
    emitter.emit_mcp("mlModel", ML_MODEL_URN, "mlModelProperties", model_props)
    ownership = OwnershipClass(owners=[OwnerClass(owner=OWNER, type=OwnershipTypeClass.TECHNICAL_OWNER)])
    emitter.emit_mcp("mlModel", ML_MODEL_URN, "ownership", ownership)
    print(f"seeded MLModel {ML_MODEL_URN} (owner riya, env PROD)")

    # 3) MLModelGroup containing the model.
    #    SPIKE: pin MLModelGroupPropertiesClass field for the model list.
    from datahub.metadata.schema_classes import MLModelGroupPropertiesClass

    group_props = MLModelGroupPropertiesClass(
        description="Fraud scoring model group (demo tail).",
        mlModels=[ML_MODEL_URN],  # SPIKE: verify field name
    )
    emitter.emit_mcp("mlModelGroup", ML_GROUP_URN, "mlModelGroupProperties", group_props)
    print(f"seeded MLModelGroup {ML_GROUP_URN}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the seed and resolve the SPIKEs**

```powershell
python seed/seed_ml_tail.py
```

Expected: prints the three "seeded" lines with no errors. Resolve each SPIKE against the live SDK/docs until all three entities exist in the UI (search `fraud_model_v4`). If `riya` does not exist as a corpuser, emit `CorpUserInfoClass` + `CorpUserStatusClass` MCPs for it (SPIKE: pin constructor) or switch `OWNER` to an existing user.

- [ ] **Step 6: Add the deliberate column-lineage gap — table-level lineage only**

```python
# append to seed_ml_tail.py main() — after step 3:
#   Table-level lineage from order_items -> FEATURE_ORDER_RISK dataset.
#   NO column mapping on purpose: the demo PR's SQL fills this gap (Moment 2).
from datahub.sdk import DataHubClient
from datahub.metadata.urns import DatasetUrn

client = DataHubClient(server=GMS_URL, token=GMS_TOKEN)
client.lineage.add_lineage(
    upstream=DatasetUrn.from_string(ORDER_ITEMS),
    downstream=DatasetUrn.from_string(FEATURE_DATASET),
    column_lineage=None,
    emit_mode="SYNC_WAIT",
)
print("seeded table-level lineage order_items -> feature_order_risk (column gap intentional)")
```

Re-run `python seed/seed_ml_tail.py`. Expected: prints the lineage line; idempotent second run completes without errors.

- [ ] **Step 7: Create the structured property `trueline.reviewed`**

Write `seed/props.yaml` (SPIKE: pin the exact `datahub properties upsert` YAML schema — `datahub properties upsert --help` first; fallback is GraphQL `createStructuredProperty`):

```yaml
properties:
  - urn: urn:li:structuredProperty:trueline.reviewed
    name: trueline_reviewed
    displayName: Reviewed by Trueline
    description: Set when Trueline gated this entity on a pull request.
    valueType: urn:li:dataType:boolean
```

```powershell
datahub properties upsert -f seed/props.yaml
```

Expected: property created (visible in UI Settings → Properties or via search). If the CLI schema differs, adjust `props.yaml` to the verified format.

- [ ] **Step 8: Write `seed/verify_graph.py`** (grows `discover_graph.py`, then delete the old file)

```python
"""Ground-truth verification: fails nonzero on any mismatch with the demo story."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from trueline.config import Config, TableRef, load_table_map
from trueline.datahub_client import DataHubGateway
from trueline.ml_impact import ml_kind

load_dotenv()

FEATURE = TableRef(platform="snowflake", db="order_entry", schema="", table="feature_order_risk")
ORDER_ITEMS = TableRef(platform="snowflake", db="order_entry", schema="", table="order_items")
MODEL_URN = "urn:li:mlModel:fraud_model_v4"


def main() -> None:
    cfg = Config()
    gateway = DataHubGateway(cfg)
    failures: list[str] = []

    results = gateway.downstream(FEATURE, max_hops=4)
    urns = {r.urn for r in results}
    for expected in ("urn:li:mlFeature:(order_entry,feature_order_risk)", MODEL_URN,
                     "urn:li:mlModelGroup:fraud-scoring"):
        if expected not in urns:
            failures.append(f"missing downstream ML entity: {expected}")
    model = next((r for r in results if r.urn == MODEL_URN), None)
    if model is None:
        failures.append("fraud_model_v4 not reachable from feature dataset")
    else:
        owners = gateway.owners(MODEL_URN)
        env = gateway.environment(MODEL_URN)
        if "riya" not in " ".join(owners).lower():
            failures.append(f"model owner missing (got {owners})")
        if env != "PROD":
            failures.append(f"model env not PROD (got {env!r})")

    cust = TableRef(platform="snowflake", db="order_entry", schema="", table="customers")
    pii = gateway.column_terms(cust, "cust_email")
    print(f"cust_email PII terms: {pii}")

    total = len(gateway.search("*", entity_type="dataset", limit=2000))
    print(f"total datasets found: {total}")
    if total < 1000:
        failures.append(f"suspiciously few datasets: {total}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        sys.exit(1)
    print("VERIFY OK — ML tail reachable, owners/env correct, pack present.")

    # Pin the table map for Task 14 (exact names discovered here).
    table_map = {
        "demo_repo/models/order_items.sql": {
            "platform": "snowflake", "db": "order_entry", "schema": "", "table": "order_items",
        },
        "demo_repo/models/feature_order_risk.sql": {
            "platform": "snowflake", "db": "order_entry", "schema": "", "table": "feature_order_risk",
        },
    }
    out = Path(__file__).resolve().parent.parent / "demo_repo" / "table_map.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table_map, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

> Note: `order_items` and `feature_order_risk` are written lowercase here; the datapack's actual case is pinned in Task 2 Step 8 — replace the db/schema/table values in `table_map.json` and in the `FEATURE`/`ORDER_ITEMS` TableRefs with the **verified** casing (e.g. `ORDER_ENTRY_DB` / `ORDER_ENTRY` / `ORDER_ITEMS`). The `TableRef` `db`/`schema` fields are used verbatim to build the URN, so casing must match the instance exactly.

- [ ] **Step 9: Run verify, delete `discover_graph.py`, write the honesty note**

```powershell
python seed/verify_graph.py
```

Expected: `VERIFY OK` with `cust_email PII terms` printed (pin the real term URN here: `_____________` — Task 10's drift detection matches on `pii` in the term URN/name).

`seed/README.md`:

```markdown
# Seed scripts

- `recipes/` — file-based ingestion recipe that creates the `FEATURE_ORDER_RISK` dataset (the official `showcase-ecommerce` datapack ships **zero ML entities**).
- `seed_ml_tail.py` — grafts the demo ML tail: dataset → MLFeature `feature_order_risk` → MLModel `fraud_model_v4` (owner @riya, env PROD) → MLModelGroup `fraud-scoring`. All entities are **demo metadata** created via real SDK calls; the product story is real, the entities are synthetic.
- `props.yaml` — `trueline.reviewed` structured property.
- `verify_graph.py` — ground-truth checks; exit code 0 = demo graph is healthy.

Reset: `datahub datapack unload showcase-ecommerce && datahub datapack load showcase-ecommerce`, then re-run `seed_ml_tail.py` + `verify_graph.py`.
```

- [ ] **Step 10: Commit**

```bash
git add seed/ demo_repo/table_map.json
git rm seed/discover_graph.py
git commit -m "feat: graft demo ML tail onto showcase datapack + graph verification"
```

---

### Task 9: state.py — SQLite (aiosqlite) journal

**Files:**
- Create: `trueline/state.py`
- Create: `tests/test_state.py`

**Interfaces:**
- Consumes: nothing.
- Produces `StateStore`:
  - `StateStore(path: Path)`
  - `async init() -> None`
  - `async record_run(run_id: str, repo: str, pr: str, commit: str, verdict: str) -> None`
  - `async proposal_exists(kind: str, target_urn: str, detail: dict) -> bool`
  - `async add_proposal(run_id: str, kind: str, target_urn: str, detail: dict) -> str` — returns id, or `""` when the proposal already exists (idempotency)
  - `async set_status(proposal_id: str, status: str) -> None`
  - `async list_proposals(status: str | None = None) -> list[dict]`
- Idempotency key: `(kind, target_urn, sha256(detail)[:16])` — unique index + `INSERT OR IGNORE`.

- [ ] **Step 1: Write the failing tests `tests/test_state.py`**

```python
import pytest

from trueline.state import StateStore


@pytest.mark.asyncio
async def test_proposal_idempotency(tmp_path):
    store = StateStore(tmp_path / "state.db")
    await store.init()
    detail = {"upstream": "u", "mapping": {"a": ["b"]}}
    first = await store.add_proposal("run-1", "LINEAGE", "urn:down", detail)
    second = await store.add_proposal("run-1", "LINEAGE", "urn:down", detail)
    assert first
    assert second == ""
    assert await store.proposal_exists("LINEAGE", "urn:down", detail)


@pytest.mark.asyncio
async def test_run_record_and_proposals(tmp_path):
    store = StateStore(tmp_path / "state.db")
    await store.init()
    await store.record_run("run-1", "trueline", "2847", "abc123", "CRITICAL")
    pid = await store.add_proposal("run-1", "GLOSSARY_TERM", "urn:x", {"column": "a", "term": "t"})
    await store.set_status(pid, "COMMITTED")
    committed = await store.list_proposals(status="COMMITTED")
    assert len(committed) == 1
    assert committed[0]["detail"]["column"] == "a"
    assert await store.proposal_exists("GLOSSARY_TERM", "urn:x", {"column": "a", "term": "t"})
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_state.py -v
```

- [ ] **Step 3: Write `trueline/state.py`**

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  repo TEXT NOT NULL, pr TEXT NOT NULL, commit TEXT NOT NULL,
  verdict TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS proposals (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  kind TEXT NOT NULL, target_urn TEXT NOT NULL,
  detail_hash TEXT NOT NULL, detail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PROPOSED',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_uniq
  ON proposals(kind, target_urn, detail_hash);
"""


def _hash(detail: dict) -> str:
    return hashlib.sha256(json.dumps(detail, sort_keys=True).encode()).hexdigest()[:16]


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()

    async def record_run(self, run_id: str, repo: str, pr: str, commit: str, verdict: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO runs (id, repo, pr, commit, verdict) VALUES (?, ?, ?, ?, ?)",
                (run_id, repo, pr, commit, verdict),
            )
            await db.commit()

    async def proposal_exists(self, kind: str, target_urn: str, detail: dict) -> bool:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT 1 FROM proposals WHERE kind=? AND target_urn=? AND detail_hash=?",
                (kind, target_urn, _hash(detail)),
            ) as cur:
                row = await cur.fetchone()
        return row is not None

    async def add_proposal(self, run_id: str, kind: str, target_urn: str, detail: dict) -> str:
        if await self.proposal_exists(kind, target_urn, detail):
            return ""
        proposal_id = f"{run_id}:{kind}:{target_urn}:{_hash(detail)}"
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO proposals (id, run_id, kind, target_urn, detail_hash, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (proposal_id, run_id, kind, target_urn, _hash(detail), json.dumps(detail, sort_keys=True)),
            )
            await db.commit()
        return proposal_id

    async def set_status(self, proposal_id: str, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE proposals SET status=? WHERE id=?", (status, proposal_id))
            await db.commit()

    async def list_proposals(self, status: str | None = None) -> list[dict]:
        query = "SELECT kind, target_urn, detail, status, run_id FROM proposals"
        params: tuple = ()
        if status is not None:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY created_at DESC"
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, params) as cur:
                rows = await cur.fetchall()
        return [
            {"kind": r[0], "target_urn": r[1], "detail": json.loads(r[2]), "status": r[3], "run_id": r[4]}
            for r in rows
        ]
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_state.py -v
```

- [ ] **Step 5: Commit**

```bash
git add trueline/state.py tests/test_state.py
git commit -m "feat: SQLite journal (aiosqlite) for idempotency and dry-run records"
```

---

### Task 10: writeback.py — propose from PR SQL, commit after merge

**Files:**
- Create: `trueline/writeback.py`
- Create: `tests/fixtures/feature_order_risk_new.sql`
- Create: `tests/test_writeback.py`

**Interfaces:**
- Consumes: `TableRef`/`parse_dataset_urn` (Task 3), gateway contract (Task 5), `StateStore` (Task 9).
- Produces:
  - `normalize_jinja(sql: str) -> str` — expands `{{ ref('x') }}` → `x`, strips other `{{...}}`.
  - `derive_column_mapping(query: str, upstream: TableRef) -> dict[str, list[str]]` — output column → upstream columns (sqlglot).
  - `Proposal` (frozen dataclass): `kind` (`LINEAGE`|`GLOSSARY_TERM`), `target_urn: str`, `detail: dict`, `source: str`.
  - `async plan_writebacks(file: ChangedFile, ref: TableRef, sql: str, gateway, source: str) -> list[Proposal]` — LINEAGE proposals for column pairs missing from the graph.
  - `async plan_term_drift(file: ChangedFile, ref: TableRef, sql: str, gateway, source: str) -> list[Proposal]` — GLOSSARY_TERM proposals propagating PII terms downstream.
  - `async apply_proposals(proposals, gateway, state: StateStore, run_id: str) -> list[tuple[Proposal, str]]` — commits with `SYNC_WAIT`; returns `(proposal, "COMMITTED"|"SKIPPED")`.

- [ ] **Step 1: Write the fixture `tests/fixtures/feature_order_risk_new.sql`**

```sql
select
    order_id,
    customer_id,
    customers.cust_email as customer_email,
    order_total,
    case when order_total > 500 then 0.4 else 0.1 end as risk_score
from {{ ref('order_items') }}
left join {{ ref('customers') }} on customers.customer_id = order_items.customer_id
```

- [ ] **Step 2: Write the failing tests `tests/test_writeback.py`**

```python
import asyncio
from pathlib import Path

from trueline.config import TableRef
from trueline.diff_parser import ChangedFile
from trueline.state import StateStore
from trueline.writeback import (apply_proposals, derive_column_mapping,
                                normalize_jinja, plan_term_drift, plan_writebacks)
from tests.fakes import CUSTOMERS, FakeGateway, FEATURE, LINEAGE, ORDER_ITEMS, TERMS

FIXTURES = Path(__file__).parent / "fixtures"
FEATURE_SQL = (FIXTURES / "feature_order_risk_new.sql").read_text(encoding="utf-8")

FILE = ChangedFile(file_path="demo_repo/models/feature_order_risk.sql", columns=(), is_sql=True)


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_normalize_jinja():
    assert normalize_jinja("from {{ ref('order_items') }}") == "from order_items"
    assert "{{" not in normalize_jinja("select * from {{ this }}")


def test_derive_column_mapping():
    mapping = derive_column_mapping(FEATURE_SQL, ORDER_ITEMS)
    assert mapping["risk_score"] == ["order_total"]
    assert mapping["order_id"] == ["order_id"]
    assert "customer_email" not in mapping
    cust_mapping = derive_column_mapping(FEATURE_SQL, CUSTOMERS)
    assert cust_mapping["customer_email"] == ["cust_email"]


def test_plan_writebacks_finds_gap():
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    proposals = run(plan_writebacks(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    assert any(p.kind == "LINEAGE" and "risk_score" in p.detail["mapping"] for p in proposals)
    assert all(p.target_urn == FEATURE.urn for p in proposals)


def test_plan_term_drift_propagates_pii():
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    proposals = run(plan_term_drift(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    pii = [p for p in proposals if p.kind == "GLOSSARY_TERM"]
    assert pii, "expected a PII propagation proposal"
    assert pii[0].detail["column"] == "customer_email"


def test_apply_proposals_commits_and_idempotent(tmp_path):
    gateway = FakeGateway(seed=LINEAGE, terms=TERMS)
    state = StateStore(tmp_path / "state.db")
    run(state.init())
    proposals = run(plan_writebacks(FILE, FEATURE, FEATURE_SQL, gateway, "PR #2847"))
    first = run(apply_proposals(proposals, gateway, state, "run-1"))
    second = run(apply_proposals(proposals, gateway, state, "run-2"))
    assert all(status == "COMMITTED" for _, status in first)
    assert all(status == "SKIPPED" for _, status in second)
    assert any(w[0] == "LINEAGE" for w in gateway.writes)
```

- [ ] **Step 3: Run tests — expect FAIL (no writeback module)**

```powershell
python -m pytest tests/test_writeback.py -v
```

- [ ] **Step 4: Write `trueline/writeback.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

import sqlglot

from .config import TableRef, parse_dataset_urn
from .datahub_client import DataHubGateway
from .diff_parser import ChangedFile
from .state import StateStore

_JINJA_REF = re.compile(r"{{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*}}")
_JINJA_OTHER = re.compile(r"{{.*?}}", re.DOTALL)


def normalize_jinja(sql: str) -> str:
    sql = _JINJA_REF.sub(r"\1", sql)
    return _JINJA_OTHER.sub("", sql)


def _base_table(select: sqlglot.exp.Select) -> str | None:
    from_ = select.find(sqlglot.exp.From)
    if from_ is None or not isinstance(from_.this, sqlglot.exp.Table):
        return None
    return from_.this.name


def derive_column_mapping(query: str, upstream: TableRef) -> dict[str, list[str]]:
    """Output column -> upstream columns, FROM-aware: bare columns bind to the
    statement's base table; qualified columns bind to their own table."""
    mapping: dict[str, list[str]] = {}
    for stmt in sqlglot.parse(normalize_jinja(query)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        base = _base_table(select)
        for expr in select.expressions:
            alias = expr.alias_or_name
            if isinstance(expr, sqlglot.exp.Column):
                if expr.table or (base and base.lower() == upstream.table.lower()):
                    mapping[alias] = [expr.name]
                continue
            cols = sorted({
                c.name for c in expr.find_all(sqlglot.exp.Column)
                if (c.table and c.table.lower() == upstream.table.lower())
                or (not c.table and base and base.lower() == upstream.table.lower())
            })
            if cols:
                mapping[alias] = cols
    return mapping


@dataclass(frozen=True)
class Proposal:
    kind: str  # LINEAGE | GLOSSARY_TERM
    target_urn: str
    detail: dict
    source: str


def _from_tables(select: sqlglot.exp.Select) -> list[str]:
    tables: list[str] = []
    for from_ in select.find_all(sqlglot.exp.From):
        if isinstance(from_.this, sqlglot.exp.Table):
            tables.append(from_.this.name)
    return tables


async def plan_writebacks(
    file: ChangedFile, ref: TableRef, sql: str, gateway: DataHubGateway, source: str
) -> list[Proposal]:
    if not sql:
        return []
    proposals: list[Proposal] = []
    for stmt in sqlglot.parse(normalize_jinja(sql)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        for table_name in _from_tables(select):
            if table_name.lower() == ref.table.lower():
                continue
            upstream = TableRef(platform=ref.platform, db=ref.db, schema=ref.schema, table=table_name, env=ref.env)
            mapping = derive_column_mapping(sql, upstream)
            if not mapping:
                continue
            missing: dict[str, list[str]] = {}
            for down_col, up_cols in mapping.items():
                present = any(
                    r.urn == ref.urn
                    for up_col in up_cols
                    for r in gateway.downstream(upstream, column=up_col, max_hops=1)
                )
                if not present:
                    missing[down_col] = up_cols
            if missing:
                proposals.append(
                    Proposal(
                        kind="LINEAGE",
                        target_urn=ref.urn,
                        detail={"upstream": upstream.urn, "mapping": missing},
                        source=source,
                    )
                )
    return proposals


async def plan_term_drift(
    file: ChangedFile, ref: TableRef, sql: str, gateway: DataHubGateway, source: str
) -> list[Proposal]:
    if not sql:
        return []
    proposals: list[Proposal] = []
    for stmt in sqlglot.parse(normalize_jinja(sql)):
        select = stmt.find(sqlglot.exp.Select)
        if select is None:
            continue
        for expr in select.expressions:
            alias = expr.alias_or_name
            for col in expr.find_all(sqlglot.exp.Column):
                if not col.table:
                    continue
                up_ref = TableRef(platform=ref.platform, db=ref.db, schema=ref.schema, table=col.table, env=ref.env)
                up_terms = gateway.column_terms(up_ref, col.name)
                pii_terms = [t for t in up_terms if "pii" in t.lower()]
                if not pii_terms:
                    continue
                down_terms = gateway.column_terms(ref, alias)
                if any("pii" in t.lower() for t in down_terms):
                    continue
                proposals.append(
                    Proposal(
                        kind="GLOSSARY_TERM",
                        target_urn=ref.urn,
                        detail={"column": alias, "term": pii_terms[0], "upstream": up_ref.urn},
                        source=source,
                    )
                )
    return proposals


async def apply_proposals(
    proposals: list[Proposal], gateway: DataHubGateway, state: StateStore, run_id: str
) -> list[tuple[Proposal, str]]:
    results: list[tuple[Proposal, str]] = []
    for p in proposals:
        if await state.proposal_exists(p.kind, p.target_urn, p.detail):
            results.append((p, "SKIPPED"))
            continue
        proposal_id = await state.add_proposal(run_id, p.kind, p.target_urn, p.detail)
        if not proposal_id:
            results.append((p, "SKIPPED"))
            continue
        if p.kind == "LINEAGE":
            upstream = parse_dataset_urn(p.detail["upstream"])
            downstream = parse_dataset_urn(p.target_urn)
            gateway.add_lineage(
                upstream=upstream,
                downstream=downstream,
                column_lineage={k: list(v) for k, v in p.detail["mapping"].items()},
                wait=True,
            )
        elif p.kind == "GLOSSARY_TERM":
            gateway.add_term(
                ref=parse_dataset_urn(p.target_urn),
                column=p.detail["column"],
                term_urn=p.detail["term"],
            )
        else:  # pragma: no cover - future kinds must be handled explicitly
            raise ValueError(f"unknown proposal kind: {p.kind}")
        await state.set_status(proposal_id, "COMMITTED")
        results.append((p, "COMMITTED"))
    return results
```

- [ ] **Step 5: Run tests — expect PASS**

```powershell
python -m pytest tests/test_writeback.py -v
```

- [ ] **Step 6: SPIKE — confirm `gateway.downstream(upstream, column=col, max_hops=1)` reflects column-level edges on the live instance** (after Task 8's graft, verify that column-filtered traversal returns `FEATURE_ORDER_RISK` only after a commit adds column lineage — this is the honest before/after check the demo relies on). Adjust `plan_writebacks` if the column filter behaves differently (e.g. compare entity `fineGrainedLineage` aspects instead).

- [ ] **Step 7: Commit**

```bash
git add trueline/writeback.py tests/fixtures/feature_order_risk_new.sql tests/test_writeback.py
git commit -m "feat: write-back planner (SQL-derived lineage) + PII drift propagation + idempotent commit"
```

---

### Task 11: comment.py — PR comment renderer

**Files:**
- Create: `trueline/comment.py`
- Create: `tests/test_comment.py`

**Interfaces:**
- Consumes: `TableVerdict` (Task 7), `Proposal` (Task 10).
- Produces: `render_comment(verdicts: list[TableVerdict], proposals: list[Proposal], dry_run: bool, author: str | None = None, summary: str | None = None) -> str` — markdown, one `VERDICT:` block per table (mirrors `DESIGN.md` §2.3), proposed write-backs list, dry-run governance note, optional LLM summary paragraph at the top.

- [ ] **Step 1: Write the failing tests `tests/test_comment.py`**

```python
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
            AffectedEntity("urn:li:mlModel:fraud_model_v4", "fraud_model_v4", "MLMODEL",
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
```

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_comment.py -v
```

- [ ] **Step 3: Write `trueline/comment.py`**

```python
from __future__ import annotations

from .impact import TableVerdict
from .writeback import Proposal

_SEV_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _readout(verdict: TableVerdict, author: str | None) -> str:
    lines = ["```"]
    for col in verdict.columns:
        lines.append(f"  {verdict.ref.table}.{col.name:<28} {col.kind.value:<10} "
                     + (f"author: @{author}" if author else ""))
    for a in verdict.affected:
        lines.append(f"  └─ {a.name:<28} {a.kind:<12} {a.reason}"
                     + (f" owner: @{a.owner}" if a.owner else ""))
    lines.append(f"  VERDICT: {verdict.severity} — {verdict.message}")
    lines.append("```")
    return "\n".join(lines)


def render_comment(
    verdicts: list[TableVerdict],
    proposals: list[Proposal],
    dry_run: bool,
    author: str | None = None,
    summary: str | None = None,
) -> str:
    worst = max(verdicts, key=lambda v: _SEV_RANK[v.severity], default=None)
    head = "PASS" if worst is None else worst.severity
    out = [
        f"## Trueline verdict — {head}",
        "",
        "Computed live from DataHub lineage (training data → features → models → deployments).",
        "",
    ]
    if summary:
        out += [summary, ""]
    for v in verdicts:
        out += [_readout(v, author), ""]
    if proposals:
        out += ["**Proposed write-backs** — applied only after merge (PR-as-approval):", ""]
        for p in proposals:
            kind = {"LINEAGE": "COLUMN LINEAGE", "GLOSSARY_TERM": "GLOSSARY TERM"}.get(p.kind, p.kind)
            out.append(f"- `{kind}` → {p.target_urn} — {p.source} — state **PROPOSED**")
        out.append("")
    if dry_run:
        out.append("_This run was dry-run: nothing was written to the graph._")
    else:
        out.append("_Write-back committed after merge: lineage is now in DataHub._")
    return "\n".join(out)
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_comment.py -v
```

- [ ] **Step 5: Commit**

```bash
git add trueline/comment.py tests/test_comment.py
git commit -m "feat: PR comment renderer (verdict readout + proposals)"
```

---

### Task 12: agent.py — Anthropic prose (facts-only contract)

**Files:**
- Create: `trueline/agent.py`
- Create: `tests/test_agent.py`

**Interfaces:**
- Consumes: `Config` (Task 3).
- Produces `Agent`:
  - `Agent(cfg: Config)`
  - `async summarize(context: dict) -> str` — returns prose (empty string when no key and no client); system prompt forbids inventing lineage/owners/metrics/severity.

- [ ] **Step 1: Write the failing tests `tests/test_agent.py`**

```python
from trueline.agent import Agent
from trueline.config import Config


class _FakeMessages:
    class _Block:
        type = "text"
        text = "Two files changed. The drop on return_date is critical because it feeds fraud_model_v4 in prod."

    def __init__(self):
        self.content = [self._Block()]

    def __getattr__(self, _):
        return None


class _FakeMessagesApi:
    def __init__(self):
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeMessages()


class _FakeClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.messages = _FakeMessagesApi()


def test_summarize_uses_client_when_key_present(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    cfg = Config()
    agent = Agent(cfg)
    fake = _FakeClient(cfg.anthropic_api_key)
    agent._client = fake
    text = agent.run_coro(agent.summarize({"verdicts": []}))
    assert "fraud_model_v4" in text
    assert fake.messages.calls and "system" in fake.messages.calls[0]


def test_summarize_returns_empty_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = Agent(Config())
    assert agent.run_coro(agent.summarize({})) == ""
```

> The test above uses `agent.run_coro` and `agent._client` — add a small helper to `Agent` (Step 3) so tests don't need their own event loop juggling: `def run_coro(self, coro): return asyncio.new_event_loop().run_until_complete(coro)` — a test-only convenience, documented as such.

- [ ] **Step 2: Run tests — expect FAIL**

```powershell
python -m pytest tests/test_agent.py -v
```

- [ ] **Step 3: Write `trueline/agent.py`**

```python
from __future__ import annotations

import asyncio
import json

from .config import Config

_SYSTEM = (
    "You are Trueline, a pull-request guard for DataHub ML lineage. "
    "You receive verified facts only: the diff, lineage paths, severities, owners, "
    "and proposed write-backs. NEVER invent lineage, owners, metrics, or severity. "
    "Write 2-4 sentences of prose that a data engineer will read at the top of the "
    "PR comment: what changed, what it hits downstream, and what to do. "
    "Do not restate every line of the diff."
)


class Agent:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = None
        if cfg.has_anthropic:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=cfg.anthropic_api_key)

    def run_coro(self, coro):  # test/CLI convenience
        return asyncio.new_event_loop().run_until_complete(coro)

    async def summarize(self, context: dict) -> str:
        if self._client is None:
            return ""
        response = await self._client.messages.create(
            model=self.cfg.anthropic_model,
            max_tokens=300,
            system=_SYSTEM,
            messages=[{"role": "user", "content": json.dumps(context, indent=2)}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
python -m pytest tests/test_agent.py -v
```

- [ ] **Step 5: SPIKE (manual, later):** set a real `ANTHROPIC_API_KEY` in `.env` and confirm one real call succeeds (run `run_local.py` in Task 13 with the key set). Without a key the pipeline still works — `summarize` returns `""` and the comment renders from engine facts (honest, and documented in README).

- [ ] **Step 6: Commit**

```bash
git add trueline/agent.py tests/test_agent.py
git commit -m "feat: Anthropic agent layer (facts-only prose; keyless fallback)"
```

---

### Task 13: run_local.py — the pipeline CLI (primary demo path)

**Files:**
- Create: `scripts/run_local.py`
- Create: `tests/e2e/test_demo_run.py`
- Create: `tests/e2e/conftest.py`

**Interfaces:**
- Consumes: everything (Tasks 3–12).
- Produces the CLI (used by the demo and the GitHub Action wrapper):
  - `python scripts/run_local.py --repo <root> --base main --head demo/pr-2847 --pr 2847 [--table-map path] [--commit] [--verify] [--json out.json] [--comment-out comment.md]`
  - Exit 0 = no CRITICAL/HIGH (PASS) · exit 1 = CRITICAL/HIGH (BLOCK) · exit 2 = infra/parse error.
  - Default `--dry-run`; writes nothing unless `--commit`.
  - `--verify` (after `--commit`): re-runs `plan_writebacks` and prints `VERIFIED: N missing edges now present in the graph` or the remaining gaps.

- [ ] **Step 1: Write `scripts/run_local.py`**

```python
#!/usr/bin/env python
"""Trueline guard pipeline for local/CI diffs (primary demo path).

Usage examples:
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847
  python scripts/run_local.py --pr 2847 --base main --head demo/pr-2847 --commit --verify
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trueline.agent import Agent  # noqa: E402
from trueline.comment import render_comment  # noqa: E402
from trueline.config import Config, load_table_map  # noqa: E402
from trueline.datahub_client import DataHubGateway  # noqa: E402
from trueline.diff_parser import parse_diff  # noqa: E402
from trueline.impact import compute_verdict  # noqa: E402
from trueline.state import StateStore  # noqa: E402
from trueline.writeback import apply_proposals, plan_term_drift, plan_writebacks  # noqa: E402

SEVERITY_EXIT = {"CRITICAL": 1, "HIGH": 1, "MEDIUM": 0, "LOW": 0}


def _verdict_to_dict(v) -> dict:
    return {
        "table": v.ref.table,
        "urn": v.ref.urn,
        "file_path": v.file_path,
        "severity": v.severity,
        "changed_columns": [{"name": c.name, "kind": c.kind.value} for c in v.columns],
        "affected": [{"urn": a.urn, "name": a.name, "kind": a.kind, "owner": a.owner, "reason": a.reason}
                     for a in v.affected],
        "message": v.message,
    }


def git_diff(repo: Path, base: str, head: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", f"{base}...{head}", "--", "*.sql"],
        capture_output=True, text=True, check=True,
    )
    return proc.stdout


async def run(args: argparse.Namespace) -> int:
    cfg = Config()
    repo = Path(args.repo)
    table_map = load_table_map(Path(args.table_map))
    gateway = DataHubGateway(cfg)
    state = StateStore(cfg.state_db)
    await state.init()
    agent = Agent(cfg)

    diff_text = git_diff(repo, args.base, args.head)
    if not diff_text.strip():
        print("no SQL changes in diff — PASS")
        return 0

    verdicts = []
    proposals = []
    for file in parse_diff(diff_text):
        ref = table_map.get(file.file_path)
        if ref is None:
            print(f"SKIP (unmapped): {file.file_path}")
            continue
        sql_path = repo / file.file_path
        sql = sql_path.read_text(encoding="utf-8") if sql_path.exists() else ""
        results = gateway.downstream(ref, max_hops=4)
        owners = {r.urn: gateway.owners(r.urn) for r in results}
        envs = {r.urn: gateway.environment(r.urn) for r in results}
        verdict = compute_verdict(ref, file, results, owners, envs)
        verdicts.append(verdict)
        source = f"PR #{args.pr} ({args.head})"
        proposals += await plan_writebacks(file, ref, sql, gateway, source)
        proposals += await plan_term_drift(file, ref, sql, gateway, source)

    for v in verdicts:
        print(f"{v.ref.table}: {v.severity} — {v.message}")

    if args.commit and not cfg.dry_run:
        run_id = f"{args.repo}:{args.pr}:{args.head}"
        results = await apply_proposals(proposals, gateway, state, run_id)
        committed = [p for p, s in results if s == "COMMITTED"]
        print(f"COMMITTED {len(committed)} write-back(s)")
    else:
        print(f"dry-run: {len(proposals)} proposal(s) would be written after merge")

    if args.verify:
        remaining = 0
        for file in parse_diff(diff_text):
            ref = table_map.get(file.file_path)
            if ref is None:
                continue
            sql_path = repo / file.file_path
            sql = sql_path.read_text(encoding="utf-8") if sql_path.exists() else ""
            remaining += len(await plan_writebacks(file, ref, sql, gateway, f"PR #{args.pr} (verify)"))
        if remaining == 0:
            print(f"VERIFIED: lineage gap closed ({len(proposals)} edge(s) now in the graph)")
        else:
            print(f"VERIFY FAILED: {remaining} missing edge(s) remain")
            return 2

    summary = agent.run_coro(agent.summarize(
        {"verdicts": [_verdict_to_dict(v) for v in verdicts],
         "proposals": [p.__dict__ for p in proposals]}
    ))
    comment = render_comment(verdicts, proposals, dry_run=not (args.commit and not cfg.dry_run),
                             author=args.author, summary=summary)
    print(comment)

    if args.comment_out:
        Path(args.comment_out).write_text(comment, encoding="utf-8")
    if args.json:
        payload = {
            "verdict": max((v.severity for v in verdicts), default="PASS"),
            "tables": [_verdict_to_dict(v) for v in verdicts],
            "proposals": [p.__dict__ for p in proposals],
            "dry_run": not (args.commit and not cfg.dry_run),
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    worst = max((v.severity for v in verdicts), default="LOW")
    return SEVERITY_EXIT[worst]


def main() -> int:
    parser = argparse.ArgumentParser(description="Trueline PR guard")
    parser.add_argument("--repo", default=str(ROOT), help="git repo root (default: this repo)")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--author", default=None)
    parser.add_argument("--table-map", default=str(ROOT / "demo_repo" / "table_map.json"))
    parser.add_argument("--commit", action="store_true", help="apply write-backs (post-merge only)")
    parser.add_argument("--verify", action="store_true", help="re-query graph after commit")
    parser.add_argument("--json", default=None, help="write machine-readable verdict to path")
    parser.add_argument("--comment-out", default=None, help="write PR comment markdown to path")
    args = parser.parse_args()
    try:
        return asyncio.new_event_loop().run_until_complete(run(args))
    except Exception as exc:  # noqa: BLE001 - CLI boundary: fail loudly, no fakes
        print(f"FATAL: {exc!r}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Write `tests/e2e/conftest.py`** (skips the suite unless a live instance is requested)

```python
import os

import pytest


@pytest.fixture(scope="session")
def e2e_enabled():
    if os.getenv("TRUELINE_E2E") != "1":
        pytest.skip("set TRUELINE_E2E=1 to run against the live quickstart")
    return True
```

- [ ] **Step 3: Write `tests/e2e/test_demo_run.py`**

```python
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_local.py"


def test_demo_pr_is_critical_dry_run(e2e_enabled):
    env = dict(os.environ)
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(ROOT), "--base", "main",
         "--head", "demo/pr-2847", "--pr", "2847", "--author", "maya",
         "--json", str(ROOT / ".trueline" / "e2e.json")],
        capture_output=True, text=True, env=env,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    payload = json.loads((ROOT / ".trueline" / "e2e.json").read_text(encoding="utf-8"))
    assert payload["verdict"] == "CRITICAL"
    assert any("fraud_model_v4" in str(t["affected"]) for t in payload["tables"])
    assert payload["dry_run"] is True
    assert "nothing was written" in out.stdout.lower()


def test_demo_pr_commit_then_verify(e2e_enabled):
    env = dict(os.environ)
    env["TRUELINE_DRY_RUN"] = "false"   # --commit only applies when dry-run is off
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(ROOT), "--base", "main",
         "--head", "demo/pr-2847", "--pr", "2847", "--commit", "--verify"],
        capture_output=True, text=True, env=env,
    )
    assert out.returncode == 1, out.stdout + out.stderr
    assert "COMMITTED" in out.stdout
    assert "VERIFIED" in out.stdout
    # second run is idempotent
    out2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(ROOT), "--base", "main",
         "--head", "demo/pr-2847", "--pr", "2847", "--commit", "--verify"],
        capture_output=True, text=True, env=env,
    )
    assert "SKIPPED" in out2.stdout
```

> The demo branches `main` + `demo/pr-2847` are created in Task 14 — this test lives here because it pins the CLI contract; it stays red until Task 14 finishes. That is expected; the task order is CLI first, branches second.

- [ ] **Step 4: Run the unit suite (e2e stays skipped)**

```powershell
python -m pytest tests -v -k "not e2e"
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_local.py tests/e2e/
git commit -m "feat: run_local.py pipeline CLI (dry-run default, commit + verify flags)"
```

---

### Task 14: demo_repo — the demo PR (branches, SQL, table map)

**Files:**
- Create: `demo_repo/README.md`
- Create: `demo_repo/models/order_items.sql` (main)
- Create: `demo_repo/models/feature_order_risk.sql` (main)
- Create: `demo_repo/models/customers.sql` (main — support only)
- Modify: `demo_repo/table_map.json` (created in Task 8; verify casing)
- Create: branch `demo/pr-2847` (modifies the two models — the demo PR)

**Interfaces:**
- Consumes: pinned table map + entity casing (Tasks 2, 8).
- Produces: the git state the e2e test and the live demo run against; the PR diff is the same content as `tests/fixtures/pr_2847.diff`.

- [ ] **Step 1: Write `demo_repo/models/order_items.sql` (on `main`)**

```sql
select
    order_id,
    customer_id,
    product_id,
    order_date,
    return_date,
    order_total
from {{ ref('orders') }}
```

- [ ] **Step 2: Write `demo_repo/models/feature_order_risk.sql` (on `main`)**

```sql
select
    order_id,
    customer_id,
    return_date,
    order_total,
    case when return_date is not null then 1.0 else 0.0 end as risk_score
from {{ ref('order_items') }}
```

- [ ] **Step 3: Write `demo_repo/models/customers.sql` (on `main`)**

```sql
select
    customer_id,
    cust_email,
    customer_name
from {{ ref('customers_raw') }}
```

- [ ] **Step 4: Verify `demo_repo/table_map.json`** matches the instance casing (from Task 8). Expected shape:

```json
{
  "demo_repo/models/order_items.sql": {
    "platform": "snowflake",
    "db": "order_entry",
    "schema": "",
    "table": "order_items",
    "env": "PROD"
  },
  "demo_repo/models/feature_order_risk.sql": {
    "platform": "snowflake",
    "db": "order_entry",
    "schema": "",
    "table": "feature_order_risk",
    "env": "PROD"
  }
}
```

(Replace db/schema/table values with the exact casing pinned in Task 2 Step 8 / Task 8 Step 3, e.g. `ORDER_ENTRY_DB`, `order_entry`, `ORDER_ITEMS` — whatever the instance actually has.)

- [ ] **Step 5: Write `demo_repo/README.md`**

```markdown
# Demo repo

The PR under test. `main` holds a healthy dbt-style project; `demo/pr-2847` is the PR
that silently breaks the fraud model.

- `models/order_items.sql` — drops `return_date` (innocent-looking cleanup; actually nulls the fraud feature).
- `models/feature_order_risk.sql` — adds `customer_email` joined from `customers` (PII drift surface).

Run: `python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847`
(The `--repo` flag points at the trueline repo root, where this directory lives.)
```

- [ ] **Step 6: Create branch `demo/pr-2847` and apply the demo PR changes**

```powershell
git add demo_repo
git commit -m "docs: demo repo (healthy models + table map)"
git checkout -b demo/pr-2847
```

Modify `demo_repo/models/order_items.sql` (remove the `return_date,` line) and `demo_repo/models/feature_order_risk.sql` (replace `return_date,` with `customer_email,` and add the customers join) so the diff matches `tests/fixtures/pr_2847.diff` exactly, then:

```powershell
git add demo_repo
git commit -m "demo: PR #2847 — drop return_date, add customer_email join (breaks the model)"
git checkout main
```

- [ ] **Step 7: Diff sync check**

```powershell
git diff main...demo/pr-2847 -- demo_repo > .trueline/pr_2847.diff
```

Compare to `tests/fixtures/pr_2847.diff` — same content (path prefix `demo_repo/` matches). Fix any drift in the fixture.

- [ ] **Step 8: Run the e2e test (live instance)**

```powershell
$env:TRUELINE_E2E="1"
python -m pytest tests/e2e -v
```

Expected: first test asserts CRITICAL + dry-run; second test commits, verifies, and shows idempotent SKIPPED on re-run. **The second test writes real lineage to the instance — run it, confirm, then reset the gap:**

```powershell
python seed/seed_ml_tail.py   # re-creates the tail; the gap is inherent (no column lineage emitted)
python seed/verify_graph.py
```

- [ ] **Step 9: Commit (on `main`)**

```bash
git add .trueline/pr_2847.diff 2>/dev/null; git add -u
git commit -m "chore: demo branches + diff fixture sync; e2e verified live"
```

---

### Task 15: skill/datahub-pr-guard — the OSS contribution

**Files:**
- Create: `skill/datahub-pr-guard/SKILL.md`
- Create: `skill/datahub-pr-guard/README.md`
- Create: `skill/datahub-pr-guard/references/severity-model.md`
- Create: `skill/datahub-pr-guard/templates/pr-verdict.template.md`
- Create: `skill/datahub-pr-guard/tests/test_skill_anatomy.py` (runs from the repo root; does not need a live instance)

**Interfaces:**
- Consumes: verified SKILL.md anatomy (ARCHITECTURE.md §8): frontmatter `name`/`description`/`user-invocable`/`min-cli-version`/`allowed-tools`; sections `Multi-Agent Compatibility`, `Not This Skill`, numbered `Step N` workflow.
- Produces: the skill directory that gets PR'd to `datahub-project/datahub-skills` (and demonstrated in Claude Code during the demo).

- [ ] **Step 1: Write `skill/datahub-pr-guard/SKILL.md`**

````markdown
---
name: datahub-pr-guard
description: Non-interactive PR/CI gate that checks a pull request's SQL/schema changes against DataHub ML lineage before merge. Use when a pull request or diff changes dbt models, SQL views, or table columns and you need to know which downstream ML features, models, deployments, and dashboards are affected — or to propose backfilling missing column lineage from the PR's own SQL. Composes datahub-lineage and datahub-enrich with an ML-aware severity model and emits a machine-readable verdict. Triggers on: "gate this PR", "what does this PR break", "check this diff against the catalog", "PR guard".
user-invocable: true
min-cli-version: 1.5.0.1rc1
allowed-tools:
  - Bash(datahub *)
---

# datahub-pr-guard

## Multi-Agent Compatibility

- **Non-interactive by design:** made for CI runs, PR bots, and agents that must not prompt. Never asks a follow-up question.
- **Deterministic first:** severity and blast radius come from the graph, not from the model. The LLM may phrase the verdict but must never invent lineage facts.
- **Idempotent:** re-running the same PR produces the same verdict and skips already-applied write-backs.

## Not This Skill

| If you need to... | Use... |
|---|---|
| Explore lineage interactively, ask "what feeds this dashboard" | `datahub-lineage` |
| Enrich an entity with tags/terms/owners ad hoc | `datahub-enrich` |
| Gate a PR / CI run on ML lineage and emit a verdict | **`datahub-pr-guard`** (this skill) |
| Backfill column lineage from a PR's SQL after merge | **`datahub-pr-guard`** (write-back step) |

## Prerequisites

- A reachable DataHub instance (Core quickstart or Cloud) with `DATAHUB_GMS_URL` and `DATAHUB_GMS_TOKEN` set.
- `datahub` CLI ≥ 1.5.0.1rc1.
- The diff of the PR: `git diff <base>...<head> -- '*.sql'`.

## Step 1: Parse the diff into changed SQL files

Use `git diff` and keep only modified `.sql` files. For each file, list the changed
column names: lines starting with `-` are DROPs, `+` are ADDs; same name on both
sides with different types is a TYPE_CHANGE.

```bash
git -C <repo> diff <base>...<head> -- '*.sql'
```

## Step 2: Resolve each file to a DataHub dataset

Map the repo-relative path to a dataset URN (project manifest or convention), then verify the entity exists:

```bash
datahub get --urn "urn:li:dataset:(urn:li:dataPlatform:snowflake,<db>.<schema>.<table>,PROD)"
```

If the entity does not exist, note it and continue — Trueline still reports the change.

## Step 3: Walk lineage downstream from each changed table

For each changed column, trace downstream through DataHub ML lineage (datasets → features → models → deployments):

```bash
datahub lineage path --from "urn:li:dataset:(...)" --to "urn:li:mlModel:..." --format json
# or MCP tools: get_lineage / get_lineage_paths_between
```

## Step 4: Apply the ML-first severity model

Use the rules in `references/severity-model.md`:
- **CRITICAL** — any ML entity (`urn:li:mlModel:*`, `urn:li:mlFeature:*`, `urn:li:mlFeatureTable:*`, `urn:li:mlPrimaryKey:*`, `urn:li:mlModelGroup:*`, `urn:li:mlModelDeployment:*`) is downstream of a changed column.
- **HIGH** — downstream dashboards/BI consumers (looker, tableau, powerbi, superset).
- **MEDIUM** — multiple downstream consumers, or any non-additive change.
- **LOW** — additive changes only.

Owners come from the entities' ownership aspect — never invented. Name them in the verdict.

## Step 5: Emit the machine-readable verdict

Output the verdict as `trueline-verdict.json` (schema in `templates/pr-verdict.template.md`):

```json
{
  "verdict": "CRITICAL",
  "tables": [
    {
      "table": "ORDER_ITEMS",
      "urn": "urn:li:dataset:(...)",
      "severity": "CRITICAL",
      "affected": [
        {"urn": "urn:li:mlModel:fraud_model_v4", "kind": "MLMODEL", "owner": "riya", "env": "PROD"}
      ]
    }
  ],
  "dry_run": true
}
```

For a PR comment, render `templates/pr-verdict.template.md` with the same facts.

## Step 6: Write-back (post-merge only — the PR is the approval)

Before merge: nothing is written; the verdict lists **PROPOSED** write-backs. After
merge: for each SQL change, derive column mappings from the PR's own SQL and backfill
missing column lineage:

```bash
datahub lineage path --from <upstream> --to <downstream> --format json  # check what exists
```

Then add the missing column lineage via the SDK (`add_lineage` with a column map) —
`datahub` CLI has no column-lineage add command. Propagation of glossary terms
(e.g. PII drifting downstream) uses the entity update pattern. Record every write in
the state journal (SQLite) so re-runs are `SKIPPED`.

## References

- `references/severity-model.md` — the ML-first severity rules and examples.
- `templates/pr-verdict.template.md` — verdict JSON schema and PR comment template.
- Shipped skills it composes: `datahub-lineage`, `datahub-enrich`.

## Common Mistakes

- Using the LLM to compute severity — always deterministic from the graph.
- Writing lineage before merge — dry-run until the PR merges.
- Adding column lineage for ML entities via `add_lineage` — ML edges are aspect fields; column lineage is Dataset → Dataset only.
- Claiming owners/env without reading the ownership/instance aspects.

## Red Flags

- The graph returns no lineage at all for a table the PR changes — say so; do not assume it is safe.
- The PR SQL references a table that is not in the catalog — flag the gap, do not invent it.
- Severity claims without a lineage path — every CRITICAL must cite the path.
````

- [ ] **Step 2: Write `skill/datahub-pr-guard/references/severity-model.md`**

```markdown
# ML-first severity model

Severity is computed deterministically from DataHub lineage, in this order:

| Severity | Rule | Example |
|---|---|---|
| CRITICAL | Any ML entity downstream of a changed column (`urn:li:mlModel:*`, `urn:li:mlFeature:*`, `urn:li:mlFeatureTable:*`, `urn:li:mlPrimaryKey:*`, `urn:li:mlModelGroup:*`, `urn:li:mlModelDeployment:*`) | Dropping `return_date` nulls `feature_order_risk` → `fraud_model_v4` |
| HIGH | Downstream dashboard/BI consumers (platforms: looker, tableau, powerbi, superset) | Change hits a Looker explore |
| MEDIUM | Multiple downstream datasets, or any non-additive change with no stronger signal | Column type change with one downstream table |
| LOW | Additive changes only (new columns), no downstream ML/dashboards | Adding a new column |

Owners are read from the ownership aspect; environment (PROD) from the entity's
custom properties / instance. Never invent either. Every CRITICAL verdict must cite
the lineage path it was computed from.
```

- [ ] **Step 3: Write `skill/datahub-pr-guard/templates/pr-verdict.template.md`**

```markdown
## Trueline verdict — {{ VERDICT }}

Computed live from DataHub lineage (training data → features → models → deployments).

```
{% for table in tables -%}
  {{ table.table }}.{{ table.column }}        {{ table.change_kind }}        author: @{{ author }}
  {% for a in table.affected -%}
  └─ {{ a.name }}        {{ a.kind }}        {{ a.reason }}        {% if a.owner %}owner: @{{ a.owner }}{% endif %}
  {% endfor -%}
  VERDICT: {{ table.severity }} — {{ table.message }}
{% endfor -%}
```

{% for p in proposals %}
- `{{ p.kind }}` → {{ p.target_urn }} — {{ p.source }} — state **{{ p.state }}**
{% endfor %}

{% if dry_run %}_This run was dry-run: nothing was written to the graph._{% else %}_Write-back committed after merge._{% endif %}
```

JSON schema (machine-readable verdict, `trueline-verdict.json`):

```json
{
  "verdict": "CRITICAL | HIGH | MEDIUM | LOW | PASS",
  "tables": [
    {
      "table": "string",
      "urn": "string",
      "severity": "string",
      "changed_columns": [{"name": "string", "kind": "DROP|ADD|TYPE_CHANGE"}],
      "affected": [{"urn": "string", "kind": "string", "owner": "string|null", "env": "string|null"}],
      "message": "string"
    }
  ],
  "proposals": [{"kind": "LINEAGE|GLOSSARY_TERM", "target_urn": "string", "detail": {}, "source": "string"}],
  "dry_run": true
}
```

- [ ] **Step 4: Write `skill/datahub-pr-guard/README.md`**

```markdown
# datahub-pr-guard

Non-interactive PR/CI gate for DataHub ML lineage. Part of the Trueline project
(see `ARCHITECTURE.md` in the repo root). Composes `datahub-lineage` + `datahub-enrich`
with an ML-aware severity model; emits a machine-readable verdict; backfills missing
column lineage from the PR's own SQL after merge (PR-as-approval).

Install with the DataHub skills flow: `npx skills add datahub-project/datahub-skills`
(after this PR merges).
```

- [ ] **Step 5: Write the anatomy test `skill/datahub-pr-guard/tests/test_skill_anatomy.py`** (top-level `tests/` is reserved for unit tests; this file lives with the skill so it ships with the PR)

```python
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent


def test_frontmatter_anatomy():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---")
    front = text.split("---")[1]
    for key in ("name:", "description:", "user-invocable:", "min-cli-version:", "allowed-tools:"):
        assert key in front, f"missing frontmatter key {key}"
    assert "Bash(datahub *)" in front


def test_required_sections():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    for section in ("## Multi-Agent Compatibility", "## Not This Skill", "## Step 1", "## Step 6",
                    "## Common Mistakes", "## Red Flags"):
        assert section in text


def test_references_and_templates_exist():
    assert (SKILL_DIR / "references" / "severity-model.md").exists()
    assert (SKILL_DIR / "templates" / "pr-verdict.template.md").exists()
```

- [ ] **Step 6: Run the anatomy test**

```powershell
python -m pytest skill/datahub-pr-guard/tests -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add skill/
git commit -m "feat: datahub-pr-guard skill (SKILL.md, severity model, verdict template)"
```

---

### Task 16: GitHub Action, README, LICENSE — submission wiring

**Files:**
- Create: `.github/workflows/trueline.yml`
- Create: `README.md`
- Create: `LICENSE` (Apache 2.0 text)
- Modify: `.env.example` (no change needed)

**Interfaces:**
- Consumes: the CLI (Task 13), the skill (Task 15).
- Produces: the public-repo submission package + CI wiring for self-hosted-runner PRs.

- [ ] **Step 1: Write `.github/workflows/trueline.yml`**

```yaml
name: trueline-guard

on:
  pull_request:
    paths: ["demo_repo/**", "**/*.sql"]
  push:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  guard:
    # Hosted runners cannot reach a local quickstart. Use a self-hosted runner on
    # the machine running `datahub docker quickstart` (primary demo path), or run
    # scripts/run_local.py locally — see README.
    runs-on: [self-hosted]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: python -m pip install -e ".[dev]"
      - name: Run guard (dry-run)
        id: guard
        shell: pwsh
        env:
          DATAHUB_GMS_URL: ${{ secrets.DATAHUB_GMS_URL }}
          DATAHUB_GMS_TOKEN: ${{ secrets.DATAHUB_GMS_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          TRUELINE_DRY_RUN: "true"
        run: |
          $ErrorActionPreference = "Continue"
          python scripts/run_local.py `
            --repo . --base origin/main --head ${{ github.head_ref }} `
            --pr ${{ github.event.pull_request.number }} `
            --author "${{ github.event.pull_request.user.login }}" `
            --json trueline-verdict.json --comment-out trueline-comment.md
          $code = $LASTEXITCODE
          if ($code -gt 1) { exit $code }   # BLOCK (1) is a valid verdict; 2 = infra/parse error
      - name: Post comment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh pr comment ${{ github.event.pull_request.number }} --body-file trueline-comment.md

  writeback:
    # Post-merge only: the PR is the approval gate (PR-as-approval).
    if: github.event_name == 'push'
    runs-on: [self-hosted]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: python -m pip install -e ".[dev]"
      - name: Apply write-backs (merge)
        shell: pwsh
        env:
          DATAHUB_GMS_URL: ${{ secrets.DATAHUB_GMS_URL }}
          DATAHUB_GMS_TOKEN: ${{ secrets.DATAHUB_GMS_TOKEN }}
          TRUELINE_DRY_RUN: "false"
        run: |
          python scripts/run_local.py `
            --repo . --base HEAD~1 --head HEAD --pr ${{ github.sha }} --commit --verify
```

- [ ] **Step 2: Write `README.md`**

```markdown
# Trueline — gate pull requests on DataHub ML lineage

Trueline reads DataHub's end-to-end ML lineage (training data → features → models →
deployments) at pull-request time, names the prod models a change silently breaks,
and — after the PR merges — writes the missing column lineage back to the graph from
the PR's own SQL. Every PR leaves the catalog more true than it found it.

Built for **Build with DataHub — The Agent Hackathon** · primary track
**Production ML Agents**. Apache 2.0.

## The three demo moments

1. **The red PR** — an innocent-looking drop (`return_date`) turns a PR red: it nulls
   `feature_order_risk` → degrades `fraud_model_v4` in prod (owner @riya).
2. **The graph gets truer** — on merge, Trueline infers column lineage from the PR's
   SQL and writes it back with provenance.
3. **Governance drift caught** — a PII term (`customers.cust_email`) that never
   propagated is detected and proposed.

## Setup (reproduce from scratch)

```powershell
pip install --upgrade acryl-datahub
datahub docker quickstart          # Docker is dev infrastructure only; the product is Docker-free
datahub datapack load showcase-ecommerce
# UI http://localhost:9002 (datahub/datahub) -> Settings -> Access Tokens -> create
# paste token into .env (see .env.example)
python seed/seed_ml_tail.py        # grafts the DEMO ML tail (the pack ships zero ML entities)
python seed/verify_graph.py        # ground-truth checks
```

## Run the guard

```powershell
python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847
```

Dry-run by default: proposes, writes nothing. `--commit --verify` applies after merge
and re-queries the graph to prove the gap closed. Exit codes: 0 PASS · 1 BLOCK ·
2 error. On GitHub, the Action runs the same CLI (self-hosted runner — hosted runners
cannot reach a local quickstart).

## OSS contribution

`skill/datahub-pr-guard` — a new skill for `datahub-project/datahub-skills`
(non-interactive PR gate composing `datahub-lineage` + `datahub-enrich` with an
ML-aware severity model). PR link: <LINK> (insert after opening the PR).

## Honesty notes

- The ML tail (`feature_order_risk`, `fraud_model_v4`, `fraud-scoring`) is **demo
  metadata** grafted onto the official showcase-ecommerce datapack, which ships zero
  ML entities. Created with real SDK calls; labeled as demo entities in `seed/README.md`.
- Every verdict is computed live from the graph. No canned comments, no invented
  metrics (no null-rate or latency numbers anywhere).
- Without `ANTHROPIC_API_KEY` the agent runs in heuristic mode: comments render from
  engine facts; nothing is fabricated.

## Criteria map

| Criterion | Where |
|---|---|
| Use of DataHub | SDK reads (lineage/ownership/terms) + SDK writes (lineage/terms) + MCP (agent layer) + structured property `trueline.reviewed` + new skill |
| Technical Execution | deterministic engine + LLM prose split; e2e-tested pipeline |
| Originality | PR-gated ML lineage + write-back from PR SQL |
| Real-World Usefulness | silent model degradation caught before merge |
| Submission Quality | this README, demo video, reproducible setup |
| Bonus OSS | `datahub-pr-guard` skill PR |

## License

Apache 2.0 — see LICENSE.
```

- [ ] **Step 3: Add the Apache 2.0 LICENSE**

```powershell
Invoke-WebRequest -UseBasicParsing https://www.apache.org/licenses/LICENSE-2.0.txt -OutFile LICENSE
```

Expected: file starts with `Apache License`.

- [ ] **Step 4: Run the full suite (unit + e2e + skill anatomy) and the seed verify**

```powershell
python -m pytest tests skill/datahub-pr-guard/tests -v
$env:TRUELINE_E2E="1"; python -m pytest tests/e2e -v
python seed/verify_graph.py
```

Expected: all green; e2e test 2 resets the gap afterward (`python seed/seed_ml_tail.py`).

- [ ] **Step 5: Commit**

```bash
git add .github README.md LICENSE
git commit -m "feat: GitHub Action, submission README, Apache 2.0 LICENSE"
```

---

## Out of scope (next plans)

- **Web app** (Next.js landing + `/gates`, `/lineage`, `/proposals`, `/settings`) — per `DESIGN.md`; the CLI/journal/graph are its data sources.
- **Demo video** (≤3 min, wow moment first) and **Devpost write-up**.
- **Public repo push + OSS skill PR** to `datahub-project/datahub-skills`.
- **Cloud trial fallback** (only if the local quickstart fails).

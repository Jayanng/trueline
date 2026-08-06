# Trueline — Architecture

> **One-liner:** Trueline turns every pull request into verified DataHub ML lineage — catching silent breakage of production ML models before they cost money, and closing the graph's lineage gaps automatically.

> **Hackathon:** Build with DataHub — The Agent Hackathon (deadline Aug 10, 2026, 5:00pm EDT)
> **Primary track:** Production ML Agents — *"Build agents for ML teams that protect models in production. Use DataHub's end-to-end ML lineage — training data → features → models → deployments — accessed via the Agent Context Kit or MCP Server to catch silent problems that can break ML systems before they cost money."*
> **Stack:** Python 3.10+ · GMI Cloud (DeepSeek V4 Flash, optional prose) · GitHub Actions · **DataHub Core (local quickstart)** — Docker only on the dev machine; the product itself is Docker-free · SQLite via aiosqlite (async) for local state · **MCP Server** for catalog reads
> **Submission requirements (confirmed via registration email):** public repo under **Apache 2.0**, working demo, ≤3-min video, by **Aug 10, 2026, 5:00pm EDT**.
> **Design:** `DESIGN.md` (UI spec — GMI Cloud aesthetic)
> **Demo path:** `scripts/run_local.py` + `seed/seed_ml_tail.py` (feature → model → group → **deployment**)

---

## 1. The thesis (why this wins)

Production ML fails silently. The model doesn't crash — the column disappears, the feature nulls, and the degradation compounds until a business metric bleeds. The track brief names it: **catch silent problems before they cost money.**

DataHub is the only place the full ML lineage path — training data → features → models → deployments — is modeled as a graph, and the Agent Context Kit / MCP Server gives agents direct access to that graph. Trueline is the agent that *uses* the graph at the exact moment ground truth is known: the pull request.

**The leverage:** Trueline sits on the PR — the moment a data change's truth is known. The code diff *is* the authoritative source of what the lineage actually is. So Trueline does two things at once:

1. **Guards** — traces every changed column downstream through DataHub ML lineage, names the affected features, models, deployments, and owners, and returns a severity verdict *before merge*.
2. **Trues the graph** — parses the PR's SQL/dbt to infer the column-level lineage DataHub was missing and writes it back with provenance.

Every PR Trueline reviews leaves DataHub **more complete and more true than it found it.** That is compounding value — the thing DataHub cannot get any other way, because only the PR knows the truth.

**ML-first framing (primary track):** ML impact is not a special case — it is the default concern. Any changed column whose downstream path reaches an `MLFeature`, `MLModel`, or deployment endpoint is **CRITICAL** by definition. Dashboards/BI consumers are secondary (HIGH). The demo is narrated as *protecting production ML*, not as generic PR review.

### How it maps to the official judging criteria (equally weighted)

> **Stage One (pass/fail):** viability — must fit the theme and reasonably apply the required APIs/SDKs. Trueline passes: **MCP Server** + Python SDK + a contributed DataHub Skill, all on the Production ML Agents theme.
> **Tie-breaking:** "the tied Submission with the highest score in the first applicable criterion" — **Use of DataHub is criterion #1 and breaks ties.** Over-invest there.

| Criterion | How Trueline scores |
|---|---|
| **Use of DataHub** | Reads the full context graph — **lineage** (dataset → feature → model → deployment paths), **ML metadata** (MLFeature/MLModel/deployments), **schemas** (changed columns), **ownership** (named owners on verdicts), **governance signals** (PII glossary terms) — via the **Agent Context Kit / MCP Server**, and **contributes back to the graph** via the **Python SDK** (lineage writes), MCP mutation tools (terms/tags/descriptions), and a **structured property** (`trueline:reviewed`) stamped on every gated dataset. Composes DataHub, never rebuilds it. |
| **Technical Execution** | Small surface: a GitHub Action (or `run_local.py`) + one agent + one new skill against a seeded local instance. Runs end-to-end; deterministic engine + LLM judgment separation keeps it robust. |
| **Originality** | Silent-ML-breakage PR gating + PR-time lineage backfill is unaddressed by shipped skills. Composes `datahub-lineage`/`datahub-enrich` — explicitly the "building on top of shipped features" behavior the rubric welcomes; rebuilds nothing. |
| **Real-World Usefulness** | Silent model degradation is a universal, expensive fear on every ML team. The PR gate lives where engineers already work; write-back is gated and reversible. |
| **Submission Quality** | ≤3-min demo video (wow moment first), written description mapping to these criteria, README reproducible from scratch (official quickstart setup; Docker only on the dev machine). |
| **Bonus (OSS)** | New skill `datahub-pr-guard` PR'd to `datahub-project/datahub-skills`; per the rubric, existing contributions extended for the hackathon also count — cite any prior/relevant contribution in the README. |

---

## 2. What DataHub actually gives us (verified from official docs, v1.6.0, Aug 2026)

### 2.1 The instance — DataHub Core, local quickstart (official path)

The hackathon's official onboarding prescribes this — and it's what judges can reproduce exactly:

- **Install:** `pip install --upgrade acryl-datahub`; **Docker Desktop** on the dev machine (the *product* stays Docker-free — this is dev infrastructure only).
- **Start:** `datahub docker quickstart` → UI **http://localhost:9002** (datahub/datahub), **GMS http://localhost:8080**.
- **Seed:** `datahub init` → `datahub datapack load showcase-ecommerce`.
- **Auth:** Personal Access Token (UI → Settings → Access Tokens), or service account token (Core v1.4.0+); Default View scoping (Core v1.6.0+).
- **CI connectivity:** localhost is unreachable from hosted GitHub runners → the demo runs the guard via `scripts/run_local.py` against a local diff (primary path), or the Action on a **self-hosted runner** on the demo machine; both documented in the README.
- **Optional alternative (same APIs):** DataHub Cloud trial `https://<tenant>.acryl.io` — SDK `/gms`, managed MCP `/integrations/ai/mcp` — kept as the fallback if the local quickstart fails on the dev machine.

### 2.2 The datapack — showcase-ecommerce

- **~1,065 entities** (docs cite ~1,049 — approximate), order-entry e-commerce: **S3 → Postgres → dbt → Snowflake → Looker / PowerBI / Tableau** (no Spark entities despite docs mentioning it). Includes domains, data products, glossary, ownership, and **existing column-level lineage** (32 dataset aspects carry `fineGrainedLineage`, e.g. dbt→snowflake `order_items.return_date`).
- Real tables (db `order_entry_db`, schema `order_entry`; case variants `ORDER_ENTRY_DB`/`ANALYTICS` on dbt): `orders`, `order_items`, `customers`, `products`, `regions`, `countries`, etc. — `order_items` carries `return_date`; `customers` carries **`cust_email`** (the PII column — *not* `email`).
- **⚠️ CRITICAL: the pack has ZERO ML entities.** The ML tail (`feature_order_risk → fraud_model_v4 → fraud-scoring`) does not exist until we graft it via the SDK (Batch 1 of the new build plan). This is the single most important fact for the demo.
- Reset: `datahub datapack unload showcase-ecommerce` then reload.

### 2.3 Reading context — MCP Server (how the agent reads)

- **Self-hosted server (default — local Core):** `uvx mcp-server-datahub@latest` with `DATAHUB_GMS_URL=http://localhost:8080` and `DATAHUB_GMS_TOKEN=<PAT>`; mutation tools enabled via `TOOLS_IS_MUTATION_ENABLED=true` (v0.5.0+, **works on Core**).
- **Managed endpoint** (optional, Cloud only): `https://<tenant>.acryl.io/integrations/ai/mcp/` with `Authorization: Bearer <token>`.
- **Read tools (verified):** `search`, `get_entities`, `list_schema_fields`, `get_lineage`, `get_lineage_paths_between`, `get_dataset_queries`, `search_documents`, `grep_documents`, `get_me`.
- **Mutation tools (verified):** `add_tags`/`remove_tags`, `add_terms`/`remove_terms`, `add_owners`/`remove_owners`, `set_domains`/`remove_domains`, `update_description`, `add_structured_properties`, `set_lifecycle_stage`, `save_document`, `create_glossary_term`, `add_related_terms`.
  - ⚠️ Available in `mcp-server-datahub` **v0.5.0+** and Cloud **v0.3.17+**, gated by `TOOLS_IS_MUTATION_ENABLED=true` — **they work on self-hosted Core too** (the old plan's "mutation = Cloud-only" claim was wrong).
- **Proposal tools — Cloud managed MCP only (verified):** `list_pending_proposals`, `propose_create_glossary_term`, `propose_lifecycle_stage`, `accept_or_reject_proposals` exist on the **Cloud managed MCP server but NOT in the OSS `mcp-server-datahub` repo**. On local Core they are unavailable — which is fine, our governance model is **PR-as-approval** (see §2.5). Similarly Cloud-managed-only: `find_sql_context`, `draft_sql_for_tables`, `set_lifecycle_stage`, `create_glossary_term`, `create_glossary_term_version`, `add_related_terms` — none are needed.

### 2.4 Writing back — Python SDK (how the graph gets truer)

`pip install acryl-datahub`

```python
from datahub.sdk import DataHubClient
client = DataHubClient(server="http://localhost:8080", token="<PAT>")
# or DataHubClient.from_env()
# Cloud alternative: server="https://<tenant>.acryl.io/gms"
```

**Lineage primitives (all verified in the official Lineage tutorial):**

- **Add table + column lineage** (column mapping: `True`/"auto_fuzzy" · "auto_strict" · dict `{downstream_col: [upstream_cols]}`):
  ```python
  from datahub.metadata.urns import DatasetUrn
  client.lineage.add_lineage(
      upstream=DatasetUrn(platform="snowflake", name="sales_raw"),
      downstream=DatasetUrn(platform="snowflake", name="sales_cleaned"),
      column_lineage={"id": ["id"], "total_revenue": ["revenue"]},
  )
  ```
  - ⚠️ **Column-level lineage and query nodes are only supported for Dataset → Dataset.**
- **Infer lineage from SQL (the key primitive for write-back):**
  ```python
  client.lineage.infer_lineage_from_sql(
      query_text=pr_sql, platform="snowflake",
      default_db="order_entry_db", default_schema="order_entry",
  )
  ```
- **Read blast radius (column-level, multi-hop):**
  ```python
  results = client.lineage.get_lineage(
      source_urn=DatasetUrn(platform="dbt", name="order_entry.order_items"),
      source_column="return_date", direction="downstream", max_hops=3,
  )
  # list[LineageResult(urn, type, hops, platform, name, paths=[LineagePath(...)])]
  ```
- **Filters:** `get_lineage` accepts `FilterDsl` (platform, entity_type, env).
- **Emit modes** (verified): `SYNC_PRIMARY` (default; SQL committed, search async), `SYNC_WAIT` (immediately searchable — use for before/after demo verification), `ASYNC` (queued, no read-after-write guarantee), `ASYNC_WAIT`.

> **⚠️ MCP cannot write lineage.** The MCP tool set has no lineage-mutation tool (verified — mutation tools cover tags/terms/owners/domains/descriptions/structured properties/lifecycle/documents, not lineage). All lineage writes go through the Python SDK; MCP mutation tools handle terms/tags/descriptions/properties. New build plan must respect this split.

### 2.5 Governance model — PR-as-approval (verified OSS/Cloud-compatible)

DataHub's Change Proposals are a **Cloud** workflow (`propose_*`/`accept_or_reject_proposals` tools). Trueline deliberately does *not* depend on them:

- Pre-merge runs are **dry-run**: Trueline posts its *proposed* graph changes as a PR comment and writes nothing.
- Write-back executes only **after the PR merges** (post-merge workflow run).
- The pull request is the approval gate — governance lives where engineers already work.

### 2.6 ML metadata (the primary track)

- DataHub models `MLModel`, `MLModelGroup`, `MLFeature`, `MLFeatureTable`, `MLPrimaryKey`.
- **Creation is Python-SDK-only** (verified: GraphQL cannot create ML entities; SDK can — `Create MLModel`, `Create MLFeature`, etc.).
- **⚠️ ML lineage is NOT written via `add_lineage`** (verified: the lineage SDK covers Dataset/DataJob/Dashboard/Chart only). ML edges are created through **aspect fields**:
  - Dataset → MLFeature/MLPrimaryKey: `MLFeaturePropertiesClass(sources=[dataset_urn])` (and `MLPrimaryKeyPropertiesClass`) — *"attaching a source to a feature creates lineage between the feature and the upstream dataset."*
  - Feature → FeatureTable: `MLFeatureTablePropertiesClass(mlFeatures=[...], mlPrimaryKeys=[...])`.
  - Feature → MLModel: read-modify-write `MLModelPropertiesClass(mlFeatures=[...])` (concatenate, don't overwrite).
  - Pattern: `MetadataChangeProposalWrapper` + `DatahubRestEmitter.emit_mcp(...)`, or the entity classes (`MLModel(...).as_mcps()`) for models/groups.
- Lineage path: **dataset → feature → model → deployment** — this is the graph the agent walks. A changed column reaching any ML entity = **CRITICAL** by default.

### 2.7 Skills (the OSS contribution)

- DataHub ships 5 skills (`datahub-setup`, `datahub-search`, `datahub-lineage`, `datahub-enrich`, `datahub-quality`) — install: `npx skills add datahub-project/datahub-skills` or `claude plugins install datahub-skills --from github:datahub-project/datahub-skills`.
- Skills = instructions; MCP = tools. Contributing a new skill to `datahub-project/datahub-skills` **counts toward the bonus OSS criterion** (confirmed on the Devpost Resources page).
- **Our contribution: `datahub-pr-guard`** — the non-interactive, PR/CI-triggered gate with an **ML-aware severity model** (downstream `MLModel`/`MLFeature`/deployment = CRITICAL) that emits a machine-readable verdict and backfills lineage by composing `datahub-lineage` + `datahub-enrich`. It is *not* a rebuild of the interactive `datahub-lineage` impact-analysis skill.

---

## 3. The three demo moments (the whole submission points here)

> The narrative is ML-first, per the track: "catch silent problems that can break ML systems before they cost money."
> Wow-moment analysis (hackathon-wow-detector): the Red PR verdict is the **primary wow moment** — the other two beats amplify it. Demo placement: the Red PR is the *first* beat, at ~28% of a 3-min runtime (20s pain framing → 10s diff reveal → 20s verdict landing). The landing page tour comes after, never before.

- **Moment 1 — "The red PR" (THE wow moment — lead with this).** A contributor opens an innocent-looking PR that drops/renames `return_date` on the `order_items` dbt model. Trueline comments: *severity CRITICAL — this nulls `feature_order_risk` → silently degrades `fraud_model_v4` in prod (owner @riya)*, with the exact lineage path (dataset → feature → model → deployment). The BI dashboards downstream are flagged HIGH. A green PR turns red.
  - **Contrast setup:** show the diff *first*, alone, as the contributor sees it — one line, `- return_date`, "this looks like a cleanup." Then the verdict lands. Innocent-looking → catastrophic blast radius is the whole emotional arc.
  - **Visual framing:** zoom into the single line `fraud_model_v4 [PROD] DEGRADING owner: @riya` and the red-flickering edge on the lineage diagram — not the whole comment.
  - **Narration timing:** 2-second silence after the verdict lands, then: *"No alert fired. The model didn't crash. That's the whole problem — and it just got caught at the only moment it could still be stopped."*
  - **Live, not recorded:** open a real PR in the demo repo during the demo; the comment posts in real time.
- **Moment 2 — "The graph got smarter" (the 100x follow-up).** Trueline parses the PR's SQL, discovers column-level lineage DataHub was missing, and (on merge) writes it back via the SDK with provenance. Show the DataHub lineage UI **before** (gap) and **after** (Trueline filled it). Narrated as the second half of the *same* PR: "and that's only half of what this PR does."
- **Moment 3 — "It caught what governance missed" (the novelty).** The same PR touches a table downstream of `customers.cust_email`, which carries a `PII` glossary term that never propagated. Trueline detects the drift and proposes propagating `PII` downstream — via the SDK term pattern (`entity["col"].add_term(urn)` + `client.entities.update(...)`) or the MCP `add_terms` tool — the catalog was *incomplete and untrue*, and Trueline closed the gap.

**Governance:** every write-back is *proposed in the PR comment first* and committed to the graph *only after the PR merges* — PR-as-approval (§2.5).

**Expected judge reactions (and the answers they unlock):**
- *"Wait — it caught a model it never met?"* → the deterministic impact engine walks real lineage; the LLM never invents facts.
- *"And it wrote back to DataHub?"* → SDK write-back with provenance, gated by PR-as-approval.

**Differentiation statement (falsifiable):** "Every other entry reads DataHub's lineage; Trueline is the only agent that gates a pull request on ML lineage *and* writes the missing lineage back to the graph from the PR's own SQL." Verify against the Devpost project gallery before submission; if a competitor already does PR-gated lineage, sharpen on the write-back half.

---

## 4. System architecture

```
                          ┌──────────────────────────────────────────┐
                          │            GitHub Pull Request             │
                          │   (dbt / SQL / schema change in a repo)    │
                          └───────────────────┬────────────────────────┘
                                              │ on: pull_request
                                              ▼
                    ┌─────────────────────────────────────────────────┐
                    │           GitHub Action: trueline-check          │
                    │  checkout → get diff → run Trueline agent (py)   │
                    │  (service-account token, Default View scoped)    │
                    └───────────────────┬─────────────────────────────┘
                                        │
              ┌─────────────────────────┼──────────────────────────────┐
              ▼                         ▼                              ▼
     ┌─────────────────┐      ┌───────────────────┐        ┌────────────────────┐
     │  DIFF PARSER    │      │   TRUELINE AGENT   │        │   WRITE-BACK        │
     │ extract changed │─────▶│  (Claude + MCP)    │───────▶│  (Python SDK)       │
     │ files, tables,  │      │  classify change,  │        │  add_lineage(),     │
     │ columns, SQL    │      │  read blast radius │        │  infer_lineage_     │
     └─────────────────┘      │  via MCP tools     │        │  from_sql(),        │
                              └─────────┬──────────┘        │  add_terms()        │
                                        │                   └──────────┬─────────┘
                              MCP (read)│                    SDK (write)│
                                        ▼                              ▼
                          ┌───────────────────────────────────────────────────┐
                          │            DataHub Core (local quickstart)         │
                          │  UI :9002 · GMS :8080 · MCP (uvx) · SDK :8080      │
                          │  lineage/ownership/ML entities + showcase datapack │
                          └───────────────────────────────────────────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────────────┐
                          │  OUTPUTS                            │
                          │  1) PR comment (severity + paths)   │
                          │  2) Lineage written back (on merge) │
                          │  3) (roadmap) "why" captured, drift │
                          └───────────────────────────────────┘
```

### Components

| Component | Responsibility | Tech |
|---|---|---|
| **GitHub Action** | Trigger on PR, fetch diff, run agent, post comment | `actions/checkout`, Python step, GitHub API (`GITHUB_TOKEN`) |
| **Diff parser** | PR diff → structured changes: file → table URN, changed columns, change type (drop/rename/type/add), extracted SQL | `sqlglot`, `unidiff` |
| **Trueline agent** | Reasoning core: classify change, read blast radius via MCP, compose severity, draft comment | Python + Anthropic SDK + DataHub MCP |
| **Impact engine** | Deterministic blast-radius walk from lineage; **ML-first severity** (any ML entity downstream = CRITICAL) | Python + DataHub SDK `get_lineage` |
| **Write-back** | Infer lineage from PR SQL, diff vs graph, write missing column lineage + provenance note; propagate governance terms; stamp `trueline:reviewed` structured property on gated datasets | Python SDK for lineage + terms (entity-update pattern) · MCP `add_structured_properties` / GraphQL for the property stamp |
| **State store** | Idempotency records (which PRs/edges already written), dry-run journal | **SQLite via aiosqlite (async)** — no external DB |
| **`datahub-pr-guard` skill** | Packaged instructions so any agent can run this PR-gate workflow | Skill dir (SKILL.md + references/ + templates/) in datahub-skills format |

### Design principle: LLM for judgment, code for facts

- **Deterministic (Python):** parsing diffs, resolving URNs, walking lineage, computing severity, writing to DataHub. Must be correct and repeatable — never delegated to the model.
- **LLM (Claude):** classifying ambiguous changes, writing the human-readable PR comment, deciding which lookups are worth doing. This keeps the demo reliable while still being "agentic" — and gives us the "0 invented lineage" claim.

### Reality principle (no mocks, no fakes — hard rule)

1. **Every verdict is computed live** from the real DataHub graph at run time. No hardcoded demo output, no canned comments, no pre-seeded verdicts.
2. **Every write-back is a real SDK call** against the real instance, verified by re-querying the graph. The before/after proof is *graph state*, not animation.
3. **The ML tail is real metadata, honestly labeled.** The entities (`feature_order_risk`, `fraud_model_v4`, `fraud-scoring`) are created with real SDK calls and real lineage — but they are *demo entities* grafted onto the showcase pack (which ships zero ML entities), and the README says so.
4. **The demo runs live** — `run_local.py` against a real diff, or a self-hosted-runner PR. No pre-recorded verdicts presented as live.
5. **The agent calls the real Anthropic API.** Without a key it fails loudly with a useful message; it never fabricates lineage.
6. **UI widgets render real data** from the app/API. Any screenshot in the README or landing page is an honest capture of a real run — never a mockup passed off as output.
7. **No fake social proof.** No invented testimonials, metrics, or customer logos anywhere in the landing page or submission.

---

## 5. Repository layout

```
trueline/
├── ARCHITECTURE.md            # this file
├── DESIGN.md                  # UI spec (landing + design system)
├── README.md                  # submission-quality; setup + demo
├── .github/workflows/
│   └── trueline.yml           # the GitHub Action (guard + write-back jobs)
├── trueline/
│   ├── __init__.py
│   ├── config.py              # env: DATAHUB_GMS_URL, token, ANTHROPIC_API_KEY
│   ├── diff_parser.py         # PR diff -> ChangedTable/ChangedColumn objects
│   ├── datahub_client.py      # thin wrapper over DataHub SDK (read + write)
│   ├── impact.py              # blast-radius engine (deterministic, ML-first)
│   ├── ml_impact.py           # ML entity detection in downstream paths
│   ├── writeback.py           # infer_lineage_from_sql + add_lineage + terms
│   ├── state.py               # SQLite (aiosqlite) idempotency/dry-run journal
│   ├── agent.py               # Claude orchestration (classify + comment)
│   └── comment.py             # render PR comment markdown
├── skill/
│   └── datahub-pr-guard/      # the OSS skill -> PR to datahub-skills
│       ├── SKILL.md
│       ├── README.md
│       ├── references/        # severity-model.md, etc.
│       └── templates/         # pr-verdict.template.md
├── seed/
│   ├── seed_ml_tail.py        # grafts ML feature/model/deployment onto the pack
│   └── demo_repo/             # sample dbt/SQL repo (order_items.sql, feature_order_risk.sql)
├── tests/
│   ├── test_diff_parser.py
│   ├── test_impact.py
│   └── fixtures/
├── scripts/
│   └── run_local.py           # run the whole pipeline against a local diff
├── pyproject.toml
└── .env.example
```

---

## 6. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Local quickstart fails on the dev machine (Docker/WSL2, RAM) | No instance to demo against | Follow the official quickstart guide (needs Docker Desktop, 8GB RAM, 13GB disk); ask Slack #agent-hackathon. Fallback: DataHub Cloud trial `https://<tenant>.acryl.io` — same APIs, no Docker |
| `infer_lineage_from_sql` chokes on demo SQL dialect | Moment 2 weak | Keep demo SQL canonical; validate early; fall back to a hand-built column mapping for the demo edge |
| GitHub Action can't reach local DataHub (localhost on hosted runners) | Live PR demo fails | Demo the guard via `scripts/run_local.py` against a local diff (primary path); or run the Action on a **self-hosted runner** on the demo machine; or an ngrok tunnel. Document the chosen path in the README |
| Write-back corrupts the seed graph mid-demo | Broken demo | Idempotent writes (SQLite journal) + `seed_ml_tail.py` reset + `datahub datapack unload/reload` + `--dry-run` flag; use `SYNC_WAIT` for the before/after verify step |
| Service-account token leaks in the Action | Security ding + real risk | Scoped service account + **Default View** + GitHub Action secrets; token in env only; document it; never commit `.env` |
| Change Proposals temptation (Cloud supports them) | Scope creep / governance story muddied | PR-as-approval is the shipped governance model; proposals only noted as available, not built |
| Rebuilding shipped DataHub features | Originality score tanks | Compose `datahub-lineage`/`datahub-enrich`; the new skill orchestrates, never reimplements |

---

## 7. Definition of "done for submission"

- [ ] Local DataHub (quickstart) seeded with showcase-ecommerce + grafted ML tail (with a deliberate column-lineage gap).
- [ ] **Public repo under Apache 2.0** (confirmed submission requirement).
- [ ] PR in demo repo triggers the guard; correct CRITICAL comment naming the prod ML model + owner; dry-run writes nothing.
- [ ] Post-merge write-back fills the missing column lineage with provenance; before/after visible in the UI.
- [ ] `datahub-pr-guard` skill runs in Claude Code; public OSS PR/RFC link exists.
- [ ] README reproducible from scratch (official quickstart setup, Docker only as dev infra); ≤3-min demo video showing all three moments.
- [ ] Written description maps to all criteria + names the track (**Production ML Agents** primary).
- [ ] Landing page per `DESIGN.md` shipped (design spec section 2).

---

## 8. Appendix — verified API quick reference

```bash
# Local Core — official quickstart path (Docker Desktop only on the dev machine)
pip install --upgrade acryl-datahub
datahub docker quickstart      # UI :9002 (datahub/datahub), GMS :8080
datahub init && datahub datapack load showcase-ecommerce

# MCP (agent reads) — self-hosted server against local GMS
claude mcp add datahub \
  -e DATAHUB_GMS_URL="http://localhost:8080" \
  -e DATAHUB_GMS_TOKEN="$PAT" \
  -e TOOLS_IS_MUTATION_ENABLED=true \
  -- uvx mcp-server-datahub@latest
# (Cloud alternative: DATAHUB_GMS_URL=https://<tenant>.acryl.io, or the managed
#  endpoint https://<tenant>.acryl.io/integrations/ai/mcp/ with Bearer token)

# Skills
npx skills add datahub-project/datahub-skills
```

```python
# Reads (SDK or MCP tools: get_lineage, get_lineage_paths_between, search, get_entities, list_schema_fields)
from datahub.sdk import DataHubClient
client = DataHubClient(server="http://localhost:8080", token="<PAT>")

downstream = client.lineage.get_lineage(
    source_urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,fct_orders,PROD)",
    source_column="user_country", direction="downstream", max_hops=3)

# Writes (verified SDK primitives)
from datahub.metadata.urns import DatasetUrn
client.lineage.infer_lineage_from_sql(
    query_text=pr_sql, platform="snowflake",
    default_db="order_entry_db", default_schema="order_entry")
client.lineage.add_lineage(
    upstream=DatasetUrn(platform="snowflake", name="order_items"),
    downstream=DatasetUrn(platform="snowflake", name="feature_order_risk"),
    column_lineage={"risk_score": ["return_date", "order_total"]})
```

**Verified MCP tools (v0.5.0+ / Cloud v0.3.17+):** read — `search`, `get_entities`, `list_schema_fields`, `get_lineage`, `get_lineage_paths_between`, `get_dataset_queries`, `search_documents`, `grep_documents`, `get_me`; mutation (env `TOOLS_IS_MUTATION_ENABLED=true`) — `add_tags`/`remove_tags`, `add_terms`/`remove_terms`, `add_owners`/`remove_owners`, `set_domains`/`remove_domains`, `update_description`, `add_structured_properties`, `set_lifecycle_stage`, `save_document`, `create_glossary_term`, `add_related_terms`; proposals — `list_pending_proposals`, `propose_create_glossary_term`, `propose_lifecycle_stage`, `accept_or_reject_proposals`.

**Verified SDK lineage API:** `add_lineage(upstream, downstream, column_lineage=True|"auto_fuzzy"|"auto_strict"|{ds_col:[up_cols]}, transformation_text=...)` · `infer_lineage_from_sql(query_text, platform, default_db, default_schema)` · `get_lineage(source_urn, source_column=..., direction, max_hops, filter=FilterDsl)` → `LineageResult(urn, type, hops, platform, name, paths)`. Column-level lineage is **Dataset → Dataset only**; **ML entities are NOT covered by `add_lineage`** — ML edges use aspect fields (`MLFeaturePropertiesClass(sources=[urn])`, `MLModelPropertiesClass(mlFeatures=[...])` via read-modify-write). Emit modes: `SYNC_PRIMARY` (default) / `SYNC_WAIT` / `ASYNC` / `ASYNC_WAIT`.

**Verified SDK entity patterns (NOT `client.entities.add_terms`/`add_owner` — get → mutate → update):**
```python
dataset = client.entities.get(DatasetUrn(platform="hive", name="realestate_db.sales", env="PROD"))
dataset["address.zipcode"].add_term(GlossaryTermUrn("Classification.Location"))
dataset.add_owner(CorpUserUrn("jdoe"))          # TECHNICAL_OWNER by default
client.entities.update(dataset)
```
Structured property `trueline:reviewed`: create once via CLI (`datahub properties upsert -f props.yaml`) or GraphQL `createStructuredProperty` (no SDK tutorial exists); attach values via MCP `add_structured_properties` (mutation enabled) or GraphQL `upsertStructuredProperties`.

**Datapack (verified on Devpost Resources):** `showcase-ecommerce` — **~1,065 entities** (docs cite ~1,049), order-entry flow S3→Postgres→dbt→Snowflake→Looker/PowerBI/Tableau, **zero ML entities** (ML tail grafted via SDK). Also: `bootstrap`, `nyc-taxi`, `healthcare`, `fiction-retail`.

**DataHub Skills (shipped):** `datahub-setup`, `datahub-search`, `datahub-lineage`, `datahub-enrich`, `datahub-quality`. **Ours: `datahub-pr-guard`** — non-interactive PR/CI gate composing lineage + enrich, adding an ML-aware severity model and a machine-readable verdict.

**SKILL.md anatomy (verified from `datahub-project/datahub-skills`):** YAML frontmatter = `name` · `description` (trigger phrases) · `user-invocable: true` · `min-cli-version` (shipped skills use `1.5.0.1rc1`) · `allowed-tools: Bash(datahub *)`. Body = `## Multi-Agent Compatibility` section, `## Not This Skill` boundary table, numbered `## Step N` workflow steps, input-validation rules, reference-docs table, common mistakes, red flags. Supports `references/` and `templates/` dirs. Useful CLI: `datahub lineage --column`, `datahub lineage path --from/--to --hops --format json`.

# Trueline — Design Spec

> **Design reference:** https://www.gmicloud.ai/en — terminal-industrial aesthetic (black canvas, lime accent, mono-first typography, hard-edged framed panels).
> **Hackathon:** Build with DataHub — The Agent Hackathon · **Primary track:** Production ML Agents
> **Project doc:** `ARCHITECTURE.md` (build plan) — this spec governs all UI/surface design.
> **Last updated:** 2026-08-06
>
> **Shipped today:** CLI + GitHub PR comment (markdown + Mermaid). Landing/app pages below are the design target; **palette + fonts are fixed** for every surface (web, PR modal, comment widgets).

---

## 0. Design identity — six principles

1. **Terminal-industrial aesthetic.** Pure black canvas, 1px `#404040` borders, zero border-radius, zero shadows, zero gradients. Everything reads as hardware/console chrome.
2. **Lime is the only accent.** One brand green powers every CTA, icon, active state, bullet, and **CRITICAL / BLOCK** emphasis. No second accent color (no red/orange for severity — lime *is* the alert on black).
3. **Mono-first typography.** GeistMono is the default voice for body, buttons, labels, and prices. The display font (Alpha Lyrae) is reserved exclusively for oversized hero titles. Headings use `font-medium` — never bold.
4. **Uppercase mono micro-typography.** Buttons, badges, and status labels are always `uppercase font-mono` with `tracking-wider` — UI as instrument-panel labels.
5. **Framed-panel composition.** Content lives in 1px-bordered frames with divide-seams (`divide-x/y`). White "card islands" break up the dark page for proof sections. No floating/shadowed cards.
6. **Animated proof over imagery.** Live client-side widgets (typewriter hero, lineage-flow diagram, incident readout) carry the proof; logos are dimmed to `invert-60 grayscale`; CTAs wink with a 45° arrow rotation on hover.

---

## 1. Design system (tokens & components)

### 1.1 Palette (locked)

| Token | Value | Usage |
|---|---|---|
| `--canvas` | `#000000` | Page background, nav, footer, PR modal scrim base |
| `--accent` | `#82C200` (lime) | All CTAs, icons, active states, bullets, CTA band, **CRITICAL chips, risk edges** |
| `--frame` | `#404040` | All 1px borders and dividers |
| `--ink` | `#FFFFFF` | Headings, primary text on dark, text on lime/black buttons |
| `--muted` | `#A3A3A3` | Body copy, captions, footer column headers, safe Mermaid nodes |
| `--band` | `#262626` | FAQ section background, PR modal body panels |
| `--card` | `#FFFFFF` | White card islands (OSS skill, pricing-style proof cells) |
| `--ink-on-card` | `#000000` | Text on white cards / text on lime chips |
| `--dim` | `white/70` | Secondary body text inside panels |

### 1.1b PR modal / gate surface tokens (same family — no new hues)

These only recombine §1.1 for the **PR verdict modal** and in-app gate expand. Do not introduce red/amber.

| Token | Value | Usage |
|---|---|---|
| `--modal-scrim` | `rgba(0,0,0,0.72)` | Backdrop over page |
| `--modal-surface` | `#000000` | Modal shell |
| `--modal-panel` | `#0A0A0A` | Inner readout / blast-radius panel |
| `--modal-band` | `#262626` | Header strip, footer actions bar |
| `--modal-frame` | `#404040` | Modal outer border (1px) |
| `--modal-frame-hot` | `#82C200` | Outer border when severity = CRITICAL (1px lime) |
| `--modal-ink` | `#FFFFFF` | Title, primary labels |
| `--modal-muted` | `#A3A3A3` | Captions, URNs, secondary |
| `--chip-critical-bg` | `#82C200` | CRITICAL / BLOCK chip fill |
| `--chip-critical-ink` | `#000000` | Text on CRITICAL chip |
| `--chip-high-bg` | transparent | HIGH chip |
| `--chip-high-frame` | `#FFFFFF` | HIGH 1px border |
| `--chip-high-ink` | `#FFFFFF` | HIGH text |
| `--chip-medium-frame` | `#404040` | MEDIUM border |
| `--chip-medium-ink` | `#A3A3A3` | MEDIUM text |
| `--chip-low-ink` | `#A3A3A3` | LOW text only |
| `--chip-pass-ink` | `#A3A3A3` | PASS |
| `--risk-edge` | `#82C200` | Mermaid / path risk stroke (dashed) |
| `--safe-node-fill` | `#000000` | Unaffected node |
| `--safe-node-stroke` | `#404040` | Unaffected node border |
| `--hot-node-fill` | `#0A0A0A` | Hot path node |
| `--hot-node-stroke` | `#82C200` | Hot path node border (2px) |

### 1.2 Typography

- **Display (hero only):** Alpha Lyrae (`alpha-lyrae-medium.woff2`), 88px desktop / 50px mobile.
- **Mono (everything else):** GeistMono (`GeistMono.woff2`).
- **Sizes:** hero title `88px` → `50px` mobile · section h2 `48px` → `32px` mobile · card h3 `24px` → `18px` mobile · body `14–18px` mono · captions/body-in-card `12–14px` mono · micro-labels `10–12px` uppercase `tracking-wider`.
- **Weights:** `font-medium` for headings; `font-regular` for body. No bold anywhere.
- **Rhythm:** section header = h2 + one-line mono description at `opacity-80`.

### 1.3 Shape language

- `border-radius: 0` everywhere.
- No shadows, no gradients (CTA band photo uses `mix-blend-multiply` — see 1.5).
- Seams: `divide-y` on vertical stacks, `divide-x` on row cells, both inside a 1px outer frame.
- Full-bleed band treatments alternate section backgrounds to pace the scroll (black → white islands → `#262626` → lime).

### 1.4 Components

| Component | Spec |
|---|---|
| **Primary button** | `bg-lime` fill, black mono uppercase text, `h-10 px-4` (hero) / `h-12 px-6` (mobile/CTA), 14px arrow SVG rotating 45° on hover (`group-hover:rotate-45 duration-200`) |
| **Ghost button** | Transparent, 1px `#404040` border, white text → lime on hover, same uppercase mono + arrow |
| **Inverted button (on lime band)** | `bg-black text-white hover:text-lime`; secondary = white fill with black text + 1px black border |
| **Badge** | Rectangular framed cell pair: left cell `border-r border-white bg-black px-3 py-2 font-mono text-sm`, right cell logo/icon (e.g. "PRODUCTION ML AGENTS TRACK" + DataHub mark) |
| **Stat rows** | Rows separated by `border-b border-[#404040]`, mono numbers large, label caption below |
| **Feature cell** | `flex items-start gap-6`, 32px lime line icon (`fill="currentColor"`), title + muted mono description |
| **Lime bullet** | `bg-lime h-1.5 w-1.5` square (not round) |
| **FAQ accordion** | Full-width trigger rows `py-6` with `border-b border-frame`, `text-lg sm:text-2xl font-medium text-white hover:text-lime`, open state lime, 16px chevron rotating 180° |
| **Code/readout panel** | Black frame, mono `text-sm`, lime prompt `$` prefix, `#404040` row separators, status chips (CRITICAL/HIGH/MEDIUM/LOW) as uppercase micro-labels — chip colors per §1.1b |
| **PR verdict modal** | See **§1.7** — full-screen instrument panel; severity drives **border + chip only**, never a second accent hue |
| **Logo marquee** | `flex w-max` auto-scroll, `gap:48px`, logos `invert-60 grayscale` |
| **Newsletter input** | Bordered mono input `h-10 font-mono text-xs` + lime submit button |

### 1.5 Motion & imagery

- **Typewriter hero** with blinking `typewriter-cursor |` block cycling words/phrases.
- **Lineage-flow diagram** (hero/wide panel): animated dataset → feature → model → deployment nodes connected by lime edges (client-rendered widget slot).
- **Hover:** `transition-colors duration-200/300`; arrows rotate 45°; accordion/nav chevrons rotate.
- **CTA band:** full-bleed lime, photographic background (e.g. mountain/GPU-cluster) at `mix-blend-multiply`, black text on top.
- **Logos:** grayscale/inverted SVG marks only. Real product proof = live widgets, never stock imagery.

### 1.6 Accessibility & detail

- Focus states: `focus-visible:ring-1 focus-visible:ring-lime` (lime ring on black).
- Disabled: `opacity-50 pointer-events-none`.
- Contrast: `#A3A3A3` on `#000000` = 7:1; lime `#82C200` on black = 5.6:1 — both AA. White text on lime = 3.3:1 — keep it large/uppercase chips/buttons only.
- All icons inline SVG (`[&_svg]:size-4` on buttons).

### 1.7 PR verdict modal (primary product surface)

The modal is how engineers meet Trueline on a PR (web) and how the **GitHub comment** should feel when rendered (markdown + Mermaid). **Colors and fonts stay in the locked system** — only density and border heat change with severity.

#### Layout

```
┌─ scrim rgba(0,0,0,0.72) ─────────────────────────────────────┐
│  ┌─ modal shell (canvas, frame 1px; CRITICAL → lime frame) ─┐ │
│  │ HEADER band (#262626)                                     │ │
│  │  [CRITICAL] [BLOCK]   PR #2847 · demo/pr-2847             │ │
│  │  mono caption · dry-run / shadow                          │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ BODY (canvas)                                             │ │
│  │  ┌ blast radius panel (#0A0A0A, frame) ─ Mermaid ───────┐ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  What if we merge?  (muted mono list)                     │ │
│  │  Notify dry-run     (cc @owners)                          │ │
│  │  ┌ terminal readout (#0A0A0A) ──────────────────────────┐ │ │
│  │  │ $ trueline --gate …                                  │ │ │
│  │  └──────────────────────────────────────────────────────┘ │ │
│  │  Proposed write-backs (divide-y rows)                     │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │ FOOTER band  ghost [View in DataHub]  lime [Copy comment] │ │
│  └───────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### Severity → chrome mapping (follow the rest of the product)

| Severity | Outer modal border | Header chip | Path edges (Mermaid) | Node (hot) |
|---|---|---|---|---|
| **CRITICAL** | `1px #82C200` | lime fill / black text `CRITICAL` + `BLOCK` | lime dashed `-.->` label `risk` | fill `#0A0A0A`, stroke `#82C200` 2px |
| **HIGH** | `1px #FFFFFF` | white border / white text `HIGH` + `WARN` | solid muted → white | stroke `#FFFFFF` |
| **MEDIUM** | `1px #404040` | frame border / muted text | solid `#404040` | stroke `#404040` |
| **LOW / PASS** | `1px #404040` | muted text only | solid `#404040` | stroke `#404040` |

#### Typography in the modal

- Title / chips: **GeistMono**, uppercase, `tracking-wider`, 10–12px chips, 14–16px body.
- No Alpha Lyrae inside the modal (display font is landing hero only).
- URNs and column names: mono, `--modal-muted`.

#### Mermaid classDefs (must match tokens)

```text
classDef broken fill:#0A0A0A,stroke:#82C200,color:#FFFFFF,stroke-width:2px
classDef safe   fill:#000000,stroke:#404040,color:#A3A3A3
```

#### GitHub PR comment (markdown)

Same hierarchy without a real modal chrome:

1. `## Trueline verdict — CRITICAL` (or LOW / HIGH…)
2. Optional LLM prose (muted paragraph — no invented facts)
3. `### Blast radius` + Mermaid (lime hot nodes)
4. `### What if we merge?`
5. `### Notify (dry-run page-out)` when CRITICAL/HIGH
6. Terminal readout fence
7. Proposed write-backs
8. Dry-run / shadow footnote

Do **not** use red/green GitHub status emojis as the primary signal; severity word + structure carry the brand.

---

## 2. Site map — exactly **5 pages** (matches the codebase)

No in-site video player. Demo video lives on **YouTube** (external link only).

| # | Route | Name | Primary codebase sources |
|---|---|---|---|
| 1 | `/` | **Landing** | README thesis, demo moments, live verdict story |
| 2 | `/guard` | **The guard** | `trueline/*`, `scripts/run_local.py`, `demo_repo/`, PR comment UX |
| 3 | `/lineage` | **ML lineage** | `datahub_client.py`, `seed/*`, `props.yaml`, track path |
| 4 | `/skill` | **OSS skill** | `skill/datahub-pr-guard/*` |
| 5 | `/start` | **Run it** | README setup, `.env.example`, seed/verify, CLI flags, Action |

Shared chrome on every page: sticky nav · framed panels · footer.  
**Not pages:** `/gates`, `/proposals`, `/settings`, `/demo` video — those are CLI / GitHub / DataHub / YouTube.

### Nav (all pages)

`TRUELINE` wordmark · **Guard** · **Lineage** · **Skill** · **Start** · ghost `GitHub` · lime `Run the guard` (→ `/start`).

---

## 3. Page specs (content must reflect real modules)

### 3.1 `/` — Landing

**Job:** Sell the Production ML Agents story in one scroll; push people to Guard / Lineage / Start.

| Section | Content (from product) |
|---|---|
| Hero | Thesis: silent ML breakage dies in review. Badge: `PRODUCTION ML AGENTS`. CTAs → `/guard`, `/start`. Optional external: `Watch on YouTube` (link only). |
| Problem | Three beats: column disappears / feature nulls / money leaks. |
| Readout panel | Real CLI-shaped output (§1.7 chrome): DROP `return_date` → feature → model → group → **deployment**, owner `@datahub`, CRITICAL. |
| Three moments | Red PR · graph gets truer · reviewed stamp — not a video. |
| Path strip | `order_items → feature_order_risk → feature → fraud_model_v4 → group + endpoint` |
| CTA | Lime → `/start` · ghost → `/skill` |

### 3.2 `/guard` — The guard (engine + PR surface)

**Job:** Explain everything that runs on a PR. Map 1:1 to Python modules.

| Block | Maps to |
|---|---|
| Pipeline steps | `diff_parser` → `datahub_client.downstream` → `ml_impact` / `impact` → `comment` → `writeback` + `state` |
| Severity table | CRITICAL (DROP/TYPE + ML) · HIGH (dashboards) · MEDIUM · LOW (additive / green PR) |
| Red vs green | `demo/pr-2847` CRITICAL · `demo/pr-safe-add` LOW |
| PR comment features | Mermaid blast radius · what-if · notify · column_suspects · `why[]` trail · shadow mode |
| CLI | `scripts/run_local.py` flags: `--commit --verify --shadow --json --notify-out` |
| Agent | Optional GMI DeepSeek **prose only** (`agent.py`) |
| Journal | SQLite proposals PROPOSED / COMMITTED / SKIPPED (`state.py`) |

### 3.3 `/lineage` — ML lineage (DataHub path)

**Job:** Show the track path and how we read/write the catalog — not a live graph UI.

| Block | Maps to |
|---|---|
| Full path diagram | dataset → MLFeature → MLModel → Group + **Deployment** |
| Read path | MCP (`get_lineage`, `search`, `get_entities`) + GMS `entitiesV2` aspects |
| Write path | SDK `add_lineage`, terms, `stamp_reviewed` / `props.yaml` |
| Seed honesty | `seed/seed_ml_tail.py` demo entities; pack has zero ML |
| Verify | `seed/verify_graph.py` ground truth |
| Env / owners | From graph + URN, never invented |

### 3.4 `/skill` — OSS skill

**Job:** Present `datahub-pr-guard` as the contribution.

| Block | Maps to |
|---|---|
| Frontmatter / triggers | `skill/datahub-pr-guard/SKILL.md` |
| Severity model | `references/severity-model.md` |
| Template | `templates/pr-verdict.template.md` |
| Boundaries | vs `datahub-lineage` / `datahub-enrich` |
| Anatomy tests | `skill/.../tests/test_skill_anatomy.py` |
| CTA | Link to skill folder + future PR on `datahub-project/datahub-skills` |

### 3.5 `/start` — Run it (no video embed)

**Job:** Reproduce the live demo from the repo. YouTube is an **external** text link only.

| Block | Maps to |
|---|---|
| Prerequisites | DataHub quickstart, token, MCP on `:8000` |
| Seed | `python seed/seed_ml_tail.py` · `python seed/verify_graph.py` |
| Env | `.env.example` — GMS, MCP, optional `GMI_*` |
| Red command | `run_local.py --head demo/pr-2847` |
| Green command | `--head demo/pr-safe-add` |
| Shadow | `--shadow` |
| Table map | `demo_repo/table_map.json` |
| CI | `.github/workflows/trueline.yml` (self-hosted) |
| Tests | `pytest tests -k "not e2e"` |
| YouTube | Single ghost link: “Watch the ≤3 min demo on YouTube” → external URL placeholder |

### 3.6 404 (not counted in the 5)

```
$ trueline --route /unknown
exit code 404 — no such route. catalog stays true.
```

---

## 4. Explicit non-pages (live elsewhere)

| Concept | Where it lives instead of a web page |
|---|---|
| Guard execution | `scripts/run_local.py` + GitHub Action |
| Live lineage browse | DataHub UI (`:9002`) |
| Write-back journal UI | SQLite via engine; list on `/guard` as docs |
| Settings UI | `.env` / `trueline/config.py` |
| Demo video | **YouTube only** |

---

## 5. Implementation notes

- **Stack:** Next.js (App Router) + Tailwind in `web/` — tokens from §1.1 / §1.1b.
- **Fonts:** Geist Mono (system fallback `ui-monospace` until woff2 lands); display optional.
- **No video iframe** on any page.
- **Content source of truth:** this IA + live modules under `trueline/`, `seed/`, `skill/`, `scripts/`.

---

## 6. Open items

- [x] Five-page IA locked to codebase (no `/gates` app shell).
- [x] No in-site demo video — YouTube external only.
- [x] PR modal tokens locked to palette (§1.1b).
- [ ] YouTube URL placeholder → real link after upload.
- [ ] Optional Alpha Lyrae woff2.
- [ ] Deploy `web/` (Vercel/static).

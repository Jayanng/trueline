# Trueline — Design Spec

> **Design reference:** https://www.gmicloud.ai/en — terminal-industrial aesthetic (black canvas, lime accent, mono-first typography, hard-edged framed panels).
> **Hackathon:** Build with DataHub — The Agent Hackathon · **Primary track:** Production ML Agents
> **Project doc:** `ARCHITECTURE.md` (build plan) — this spec governs all UI/surface design.
> **Last updated:** 2026-08-05

---

## 0. Design identity — six principles

1. **Terminal-industrial aesthetic.** Pure black canvas, 1px `#404040` borders, zero border-radius, zero shadows, zero gradients. Everything reads as hardware/console chrome.
2. **Lime is the only accent.** One brand green powers every CTA, icon, active state, and bullet. Everything else is monochrome. Never dilute it.
3. **Mono-first typography.** GeistMono is the default voice for body, buttons, labels, and prices. The display font (Alpha Lyrae) is reserved exclusively for oversized hero titles. Headings use `font-medium` — never bold.
4. **Uppercase mono micro-typography.** Buttons, badges, and status labels are always `uppercase font-mono` with `tracking-wider` — UI as instrument-panel labels.
5. **Framed-panel composition.** Content lives in 1px-bordered frames with divide-seams (`divide-x/y`). White "card islands" break up the dark page for proof sections. No floating/shadowed cards.
6. **Animated proof over imagery.** Live client-side widgets (typewriter hero, lineage-flow diagram, incident readout) carry the proof; logos are dimmed to `invert-60 grayscale`; CTAs wink with a 45° arrow rotation on hover.

---

## 1. Design system (tokens & components)

### 1.1 Palette

| Token | Value | Usage |
|---|---|---|
| `--canvas` | `#000000` | Page background, nav, footer |
| `--accent` | `#82C200` (lime) | All CTAs, icons, active states, bullets, CTA band |
| `--frame` | `#404040` | All 1px borders and dividers |
| `--ink` | `#FFFFFF` | Headings, primary text on dark, text on lime/black buttons |
| `--muted` | `#A3A3A3` | Body copy, captions, footer column headers |
| `--band` | `#262626` | FAQ section background |
| `--card` | `#FFFFFF` | White card islands (OSS skill, pricing-style proof cells) |
| `--ink-on-card` | `#000000` | Text on white cards |
| `--dim` | `white/70` | Secondary body text inside panels |

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
| **Code/readout panel** | Black frame, mono `text-sm`, lime prompt `$` prefix, `#404040` row separators, status chips (CRITICAL/HIGH/MEDIUM) as uppercase micro-labels |
| **Logo marquee** | `flex w-max` auto-scroll, `gap:48px`, logos `invert-60 grayscale` |
| **Newsletter input** | Bordered mono input `h-10 font-mono text-xs` + lime submit button |

### 1.5 Motion & imagery

- **Typewriter hero** with blinking `typewriter-cursor |` block cycling words/phrases.
- **Lineage-flow diagram** (hero/wide panel): animated dataset → feature → model → deployment nodes connected by lime edges (client-rendered widget slot).
- **Hover:** `transition-colors duration-200/300`; arrows rotate 45°; accordion/nav chevrons rotate.
- **CTA band:** full-bleed lime, photographic background (e.g. mountain/GPU-cluster) at `mix-blend-multiply`, black text on top.
- **Logos:** grayscale/inverted SVG marks only. Real product proof = live widgets, never stock imagery.

### 1.6 Accessibility & detail

- Focus states: `focus-visible:ring-1 focus-visible:ring-ring`.
- Disabled: `opacity-50 pointer-events-none`.
- Contrast: `#A3A3A3` on `#000000` = 7:1; lime `#82C200` on black = 5.6:1 — both AA. White text on lime = 3.3:1 — keep it large/bold (uppercase buttons only).
- All icons inline SVG (`[&_svg]:size-4` on buttons).

---

## 2. Landing page — structure & copy (narrative-first)

Single scroll page, 7 sections + nav + footer. Section flow below; every section header = h2 (32→48px, `font-medium`) + one-line mono description (`opacity-80`).

### 2.1 Sticky nav
Logo (white SVG wordmark) · links: Problem · How it works · Impact · OSS Skill · FAQ · ghost button "Read the architecture" (→ `ARCHITECTURE.md` rendered) · lime button "Open a demo PR" (→ `/demo`).

### 2.2 Hero — "The silent failure dies in review."
- **Badge:** `BUILT WITH DATAHUB · PRODUCTION ML AGENTS TRACK` (framed cell pair).
- **Display title (typewriter):** "Catch silent ML breakage" — typewriter cycles the tail: `before merge.` → `before training.` → `before it costs money.`
- **Tagline (mono, `opacity-80`):** "Trueline reads DataHub's end-to-end ML lineage at pull-request time — training data → features → models → deployments — and turns a green PR red before a dropped column silently degrades a model in production."
- **CTAs:** `Start the demo` (lime, → `/demo`) · `How it works` (ghost, ↓ §2.4).
- **Below (h-[20svh] mobile / full-height desktop):** live lineage-flow widget — nodes `order_items → feature_order_risk → fraud_model_v4 → fraud-scoring`, one edge blinking lime.

### 2.3 Problem — "The incident that never fired."
- **Header:** "The incident that never fired." / *"Production ML fails silently. The model doesn't crash — it degrades."*
- **Readout panel (the money visual)** — fields are real engine output (column, entity type, prod flag, owner from the graph, verdict). No invented telemetry:
```
$ trueline --diff pr/2847 --gate

  order_items.return_date        DROP        author: @maya
  └─ feature_order_risk          MLFEATURE   downstream
     └─ fraud_model_v4           MLMODEL     [PROD] owner: @riya
        └─ fraud-scoring         MLMODELGROUP downstream

  VERDICT: CRITICAL — silent prod-model breakage. Block until owner approves.
```
- **Copy row (3 feature cells):**
  - *"The column disappears."* — a rename or drop slips into a model's training input. No crash, no alert.
  - *"The feature nulls."* — the derived feature degrades silently, poisoning every downstream prediction.
  - *"The money leaks."* — degraded models cost teams weeks to trace and real revenue to fix.

### 2.4 How it works — "Review the change. Guard the model. True the graph."
- **Wide framed panel** with 3 cells separated by `divide-x`:
  1. **THE RED PR** — "Every pull request that touches data runs the Trueline guard. Changed columns are traced downstream through DataHub lineage to every ML feature, model, and deployment they feed — with owners named on the verdict."
  2. **THE GRAPH GETS TRUER** — "The diff reveals the lineage the catalog was missing. On merge, Trueline infers column-level lineage from the PR's own SQL and writes it back with provenance — DataHub got smarter because of the PR."
  3. **GOVERNANCE DRIFT CAUGHT** — "When a column feeding production loses its PII term — or a term never propagated downstream — Trueline detects the drift and proposes the fix with the lineage path shown."
- **Design note strip (mono caption):** "LLM for judgment, code for facts — blast radius and severity are computed deterministically; the agent phrases, prioritizes, and writes the human-readable verdict."

### 2.5 Impact — stat band (black, `divide-y` rows)
| Stat | Caption |
|---|---|
| `1` | merge gate — every data PR, dry-run before, write-back after |
| `3` | severity tiers — CRITICAL · HIGH · MEDIUM |
| `2` | layers per PR — guard the model, true the graph |
| `0` | invented lineage — facts from the engine, never the model |

### 2.6 OSS skill — white card island
- **Header:** "One contribution. Open source." / *"Agents for ML teams shouldn't start from zero."*
- **White framed card:** "Trueline ships `datahub-pr-guard` — a new skill for `datahub-project/datahub-skills` that turns any agent into a non-interactive PR gate with an ML-aware severity model. It composes `datahub-lineage` + `datahub-enrich`; it rebuilds nothing."
- **Buttons:** `View the skill` (black-on-white) · `datahub-skills repo` (ghost, external link).

### 2.7 FAQ — `#262626` band, accordion (right column)
1. **"Does Trueline need Docker?"** — No, the product is Docker-free. Our demo runs against a local DataHub quickstart (`datahub docker quickstart` — Docker is dev infrastructure only) or DataHub Cloud via the MCP server and Python SDK.
2. **"What does it use from DataHub?"** — The end-to-end ML lineage path (datasets → features → models → deployments), read through the Agent Context Kit / MCP tools and written through the Python SDK.
3. **"Is the LLM making lineage decisions?"** — No. A deterministic engine computes blast radius and severity from the graph; the agent classifies ambiguous changes and writes the comment.
4. **"When does write-back happen?"** — After the PR merges. The PR is the approval gate; pre-merge runs are dry-run — they propose, never mutate.
5. **"What's the open-source story?"** — A new skill, `datahub-pr-guard`, PR'd to `datahub-project/datahub-skills` — composing the shipped lineage/enrich skills with PR orchestration and an ML severity model.

### 2.8 CTA band — lime + photo
- **Headline:** "Open a PR. Break nothing. / Catalog stays true."
- **Buttons:** `Start the demo` (black-on-lime) · `Join the DataHub Slack` (white).

### 2.9 Footer
- Logo + socials (X · GitHub · LinkedIn · YouTube, muted → white hover).
- 4 mono columns: **Product** (Problem, How it works, Impact, FAQ) · **Developers** (Architecture, `datahub-pr-guard` skill, API reference) · **Resources** (Demo, DataHub docs, Agent Context Kit, MCP server) · **Community** (DataHub Slack, Devpost, datahub-skills repo).
- "Stay in the loop" newsletter (`text-2xl lg:text-[36px]`) + mono input + lime subscribe.
- Legal bar: mono `text-xs`, underlined links, `#A3A3A3` dot separators.

---

## 3. Secondary pages (inherit the design system)

All secondary pages share: sticky nav (same), `container` width, framed panels, mono uppercase micro-labels, same buttons/badges. They are **templates**, not bespoke designs.

### 3.1 `/demo` — demo page
- Hero mini: h1 `48px` + tagline.
- **Video slot:** framed black panel (16:9), embed of the ≤3-min demo video.
- **Setup:** numbered mono steps in framed rows — 1) `datahub docker quickstart` 2) `datahub datapack load showcase-ecommerce` 3) seed ML tail 4) open demo PR 5) watch the verdict land.
- **Before/after:** two framed panels side by side (`divide-x`) — lineage gap before, filled + provenance after.

### 3.2 `/architecture` — architecture & docs page
- Left sticky mono TOC (`text-sm`, `#404040` separators), right content panels: system diagram (framed), component table, API quick reference code blocks (mono, lime `$` prompts), risk table.
- Rendered from `ARCHITECTURE.md` content; same section-header rhythm.

### 3.3 `/skill` — `datahub-pr-guard` OSS skill page
- Badge: `OSS CONTRIBUTION · DATAHUB-SKILLS`.
- **SKILL.md panel:** framed "file" showing frontmatter (name, description, user-invocable, min-cli-version) in mono with lime keys.
- **Severity model table:** framed table — `CRITICAL` = reaches prod ML model/certified asset · `HIGH` = dashboards/many consumers · `MEDIUM` = internal tables · `LOW` = additive.
- **Install commands:** mono code block (`npx skills add datahub-project/datahub-skills`).
- **"Not This Skill"** boundary table (vs `datahub-lineage`, `datahub-enrich`).

### 3.4 `/docs/*` — reference pages
Generic template: breadcrumb mono caption, h2 + description header, framed content panels, right rail optional TOC. No new components.

### 3.5 404 — terminal style
```
$ trueline --route /unknown
exit code 404 — no such route. catalog stays true.
```
+ lime `Back home` button.

---

## 4. Product pages — the Trueline app

All product pages inherit the design system (§1) and share an **app shell**: top bar with logo + app nav (`Gates · Lineage · Proposals · Settings`), a status strip (mono caption: connected tenant URL + dry-run indicator), and the standard framed-panel composition. No landing-page marketing sections here — this is the instrument panel.

> **State backing:** `/gates` and `/proposals` are driven by the local SQLite (aiosqlite) store — the idempotency/dry-run journal (see `ARCHITECTURE.md` §4). `/lineage` reads live from the DataHub graph (local GMS or Cloud).

### 4.1 `/gates` — Guard console (app home)
- **Header:** "Guard console" h2 + mono caption "Every data PR, gated on ML lineage."
- **Framed table** (`border frame`, header row `uppercase font-mono text-[10px] tracking-wider text-muted`, body rows `divide-y`):
  - PR # (mono link) · changed columns (mono, comma list) · severity chip · verdict chip · owner mentions · timestamp
- **Severity chips (palette-pure):** `CRITICAL` = lime fill, black mono text · `HIGH` = white border, white text · `MEDIUM` = muted text, frame border · `LOW` = muted text only. No red/green — the palette stays black/lime.
- **Verdict chips:** `BLOCK` (lime fill) · `WARN` (white border) · `PASS` (muted).
- **Row expand:** clicking a row expands an inline lineage-path readout (mono, `#404040` separators, lime `└─` branches) — no page navigation.

### 4.2 `/gates/:pr` — Verdict detail
- **Top banner:** severity chip + verdict chip + "PR #2847 · repo/demo-repo" mono caption.
- **The readout panel** (the wow moment, reused from §2.3): the `$ trueline --diff` terminal block — changed columns, null-rate propagation, `fraud_model_v4 [PROD] DEGRADING owner: @riya`, `VERDICT: CRITICAL` line in lime.
- **Affected entities list:** framed rows per ML entity — URN (mono), type (`MLMODEL` / `MLFEATURE` / deployment), owner link, one-line reason.
- **Proposed write-backs:** framed list of every mutation Trueline *would* make — type (`COLUMN LINEAGE` / `GLOSSARY TERM` / `STRUCTURED PROPERTY`), target entity, source "inferred from PR SQL", state chip **PROPOSED** (dry-run) → **COMMITTED** after merge.
- **Governance note (mono caption):** "Write-back commits only after the PR merges. This run was dry-run: nothing was written."

### 4.3 `/lineage` — ML lineage explorer
- **Header:** "ML lineage" h2 + mono caption "Training data → features → models → deployments."
- **Flow diagram widget:** framed black panel; nodes as bordered cells (`order_items`, `feature_order_risk`, `fraud_model_v4`, `fraud-scoring`), lime edges, animated pulse; changed/dropped node or edge gets a lime blink (per demo moment 1).
- **Node click → side entity panel** (right column, `divide-x`): schema fields (mono list), owners, glossary terms, tags, description; "reviewed by Trueline · PR #2847" provenance line when stamped.
- **Before/after view (real graph state, not animation):** `before | after` segmented control renders **live queries** of the graph — before = the gap edge absent, after = edge present with Trueline provenance. The toggle flips real data, never a fake. (Reality principle, `ARCHITECTURE.md` §4.)
- **Empty state:** centered mono line "No lineage matches this search. Catalog stays true." + lime reset button.

### 4.4 `/proposals` — Write-back journal
- **Header:** "Write-back journal" h2 + mono caption "Every mutation Trueline made — or wants to make."
- **Framed list rows** (`divide-y`): mutation type chip · target entity URN (mono) · source PR + commit · provenance note · state chip (`PROPOSED` lime-border / `COMMITTED` lime-fill / `REJECTED` muted).
- **Filters:** segmented mono controls — `ALL · LINEAGE · TERMS · PROPERTY` (lime active).
- **Idempotency proof:** re-running a PR shows `SKIPPED (already applied)` state — visible evidence of the SQLite journal.
- **Empty state:** "No pending proposals. Every write is accounted for."

### 4.5 `/settings` — Connection
- **Header:** "Connection" h2 + mono caption "Point Trueline at your DataHub tenant."
- **Mono form fields** (bordered inputs, `h-10 font-mono text-xs`, focus ring lime):
  - GMS URL (`http://localhost:8080` or `https://<tenant>.acryl.io/gms`) · GMS token (masked, `••••••`) · Default View (optional) · Dry-run toggle (segmented `ON | OFF`, default ON)
- **Status row:** `CONNECTED` lime chip + latency + "service account: trueline-ci" mono caption.
- **Test button:** `Test connection` (lime) → runs `DataHubClient(...).search("*")` smoke call; result line in mono (`200 OK · 1,065 entities`).
- **Danger zone (framed, `divide-y`):** `Reset local journal` (clears SQLite store) · `Re-seed demo graph` (runs `seed_ml_tail.py`) — both ghost-bordered buttons with lime hover.

---

## 5. Implementation notes

- **Stack:** Next.js (App Router) + Tailwind CSS, mirroring GMI's build (React/Tailwind). Custom theme tokens via CSS variables (`--canvas`, `--accent`, `--frame`, `--ink`, `--muted`, `--band`, `--card`).
- **Fonts:** self-hosted `GeistMono.woff2` + `alpha-lyrae-medium.woff2` (preload, `font-display: swap`).
- **Sections:** `<section class="md:py-26 w-full px-6 py-12 sm:px-10 md:px-16">` + `container` — the standard wrapper for every section.
- **Section header component:** `flex flex-col gap-6` h2 + mono one-liner — reused everywhere (no drift).
- **Widgets:** typewriter hero (React, cycles array + CSS blink), marquee (CSS `w-max` animation), lineage-flow diagram (SVG edges + CSS transitions).
- **No image assets required** except CTA-band photo and the DataHub/NVIDIA-style badge marks; all icons inline SVG.
- **Content source of truth:** this file for copy/structure; `ARCHITECTURE.md` for facts (APIs, severities, demo moments). Keep the verdict readout (§2.3) consistent with the demo's real output.

---

## 6. Open items

- [ ] Hero display font license/asset for Alpha Lyrae (fallback: GeistMono display).
- [ ] CTA band photo asset (GPU-cluster or abstract landscape) — or pure lime fill.
- [ ] Verify typewriter phrase list matches final demo script (Moment 1 wording).
- [ ] Confirm `/demo` video slot vs Devpost upload (page may link out instead of embed).

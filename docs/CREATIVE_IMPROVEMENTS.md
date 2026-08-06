# Creative improvements (beyond the audit fixes)

Ideas ranked by **judge wow / effort**. Implemented items are marked elsewhere in the repo;
this file is the idea bank for pitch and stretch.

## High wow / medium effort

1. **Blast-radius heatmap in the PR comment**  
   ASCII or Mermaid of `order_items → feature → model → deployment` with the broken edge in red.  
   Judges *see* the path without opening DataHub.

2. **“What if we merge?” counterfactual**  
   One paragraph: estimated impact class (CRITICAL) + which online endpoint would serve bad scores.  
   Still no invented metrics — only graph facts.

3. **Green PR twin**  
   A second branch that only ADDs a column → LOW/PASS. Side-by-side proves the gate isn’t always red.

4. **Owner page-out simulation**  
   If owner is on-call (from DataHub ownership), append `cc @datahub` and a Slack-style payload JSON artifact (dry-run).

## Medium wow / low effort

5. **Severity trail in JSON**  
   `why: [{rule: "ML_DOWNSTREAM", urn, hops}]` in `trueline-verdict.json` for machine consumers.

6. **Diff-to-feature column hint**  
   When DROP name appears in feature SQL or mapping, tag `column_suspect: return_date` on the verdict.

7. **Time-to-detect framing**  
   In the video only: “Without Trueline this ships; with Trueline it blocks in 60s.”

## Stretch / future

8. **Shadow mode** — comment without blocking (exit 0 + CRITICAL label) for brownfield adoption.  
9. **Multi-repo table map** — monorepo + dbt package paths.  
10. **DataHub Cloud + hosted Action** — remove self-hosted requirement.  
11. **Human-in-the-loop accept** on write-backs via DataHub proposals (Cloud).  
12. **Cost-of-silence narrative pack** — one slide of industry silent-failure stories (no fake numbers).

## Pitch-safe creative framing

- Call the product an **“immune system for production ML”** — PRs are antibodies.  
- “The catalog compounds: every merge is a truth injection.”  
- Avoid “AI decides severity” — say “agent tools the graph; model only writes English.”

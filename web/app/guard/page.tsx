import Link from "next/link";
import { Chip, Frame, PageHero, Section, SectionHead } from "@/components/Shell";

const PIPELINE = [
  { mod: "diff_parser.py", step: "Parse PR SQL diff", detail: "DROP / ADD / TYPE_CHANGE per column" },
  { mod: "datahub_client.py", step: "Walk downstream lineage", detail: "MCP get_lineage + GMS aspects + SDK" },
  { mod: "ml_impact.py + impact.py", step: "Score severity", detail: "ML-first: CRITICAL on silent breakage" },
  { mod: "comment.py", step: "Render PR comment", detail: "Mermaid blast radius · what-if · notify" },
  { mod: "writeback.py + state.py", step: "Plan / commit write-backs", detail: "Column lineage + SQLite journal" },
  { mod: "agent.py", step: "Optional prose", detail: "GMI DeepSeek — never invents severity" },
];

const SEVERITY = [
  { sev: "CRITICAL", v: "critical" as const, rule: "DROP or TYPE_CHANGE with ML entity downstream (feature, model, group, deployment)" },
  { sev: "HIGH", v: "high" as const, rule: "Downstream dashboards / BI (looker, tableau, powerbi, …)" },
  { sev: "MEDIUM", v: "medium" as const, rule: "Multi-consumer path or non-additive change without ML" },
  { sev: "LOW", v: "low" as const, rule: "Additive-only — even if ML consumers exist (green PR path)" },
];

export default function GuardPage() {
  return (
    <>
      <PageHero
        eyebrow="Page 02 · Product"
        title="The guard."
        desc="Everything that runs when a data PR hits Trueline — mapped to modules under trueline/ and scripts/run_local.py."
      />

      <Section className="border-b border-frame">
        <SectionHead
          title="Pipeline"
          desc="Deterministic engine first. LLM only phrases the comment."
        />
        <div className="border border-frame divide-y divide-frame">
          {PIPELINE.map((p, i) => (
            <div key={p.mod} className="grid gap-2 px-4 py-4 sm:grid-cols-[3rem_1fr_1fr] sm:items-center sm:gap-6">
              <span className="text-[10px] uppercase tracking-wider text-accent">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div>
                <p className="text-sm text-ink">{p.step}</p>
                <p className="mt-1 text-xs text-muted">{p.detail}</p>
              </div>
              <code className="text-xs text-accent">{p.mod}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Severity model"
          desc="From skill/datahub-pr-guard/references/severity-model.md and impact.py."
        />
        <div className="border border-frame divide-y divide-frame">
          {SEVERITY.map((row) => (
            <div key={row.sev} className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-start sm:gap-6">
              <Chip variant={row.v}>{row.sev}</Chip>
              <p className="text-xs leading-relaxed text-muted sm:text-sm">{row.rule}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Red PR vs green PR"
          desc="demo_repo models + git branches — same engine, opposite outcomes."
        />
        <div className="grid gap-0 border border-frame md:grid-cols-2">
          <Frame hot className="border-0 border-b md:border-b-0 md:border-r">
            <div className="border-b border-frame bg-band px-4 py-2 text-[10px] uppercase tracking-wider text-accent">
              demo/pr-2847 · BLOCK
            </div>
            <div className="space-y-3 p-4 text-xs text-muted">
              <p>
                Drops <code className="text-ink">return_date</code> on{" "}
                <code className="text-ink">order_items</code> / feature SQL.
              </p>
              <p>
                Hits <code className="text-ink">fraud_model_v4</code> +{" "}
                <code className="text-ink">fraud-scoring-endpoint</code>.
              </p>
              <Chip variant="critical">CRITICAL · exit 1</Chip>
            </div>
          </Frame>
          <div className="border-frame">
            <div className="border-b border-frame bg-band px-4 py-2 text-[10px] uppercase tracking-wider text-muted">
              demo/pr-safe-add · PASS
            </div>
            <div className="space-y-3 p-4 text-xs text-muted">
              <p>
                Adds <code className="text-ink">notes</code> only — pure ADD.
              </p>
              <p>ML consumers may appear for awareness; no silent breakage.</p>
              <Chip variant="low">LOW · exit 0</Chip>
            </div>
          </div>
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="PR comment surface"
          desc="trueline/comment.py — what engineers see on GitHub (design §1.7)."
        />
        <ul className="grid gap-0 border border-frame sm:grid-cols-2">
          {[
            "Mermaid blast radius (lime hot path, brand tokens)",
            "What if we merge? — graph facts only",
            "Notify dry-run — cc owners from ownership aspect",
            "column_suspects — DROP / TYPE_CHANGE names",
            "why[] severity trail in --json payload",
            "--shadow — comment CRITICAL, exit 0",
          ].map((item) => (
            <li
              key={item}
              className="border-b border-frame px-4 py-3 text-xs text-muted last:border-b-0 sm:border-r sm:odd:border-r sm:[&:nth-child(2n)]:border-r-0"
            >
              <span className="mr-2 inline-block h-1.5 w-1.5 bg-accent align-middle" />
              {item}
            </li>
          ))}
        </ul>
      </Section>

      <Section>
        <SectionHead
          title="CLI entrypoint"
          desc="scripts/run_local.py — primary demo and GitHub Action path."
        />
        <Frame className="p-4">
          <pre className="overflow-x-auto text-xs text-muted">
            <span className="text-accent">$</span> python scripts/run_local.py \{"\n"}
            {"    --repo . --base main --head demo/pr-2847 --pr 2847 \\"}{"\n"}
            {"    --json .trueline/verdict.json \\"}{"\n"}
            {"    --comment-out .trueline/comment.md \\"}{"\n"}
            {"    --notify-out .trueline/notify.json"}
          </pre>
        </Frame>
        <p className="mt-4 text-xs text-muted">
          Also: <code className="text-ink">--commit --verify</code> post-merge ·{" "}
          <code className="text-ink">--shadow</code> brownfield · Action in{" "}
          <code className="text-ink">.github/workflows/trueline.yml</code>
        </p>
        <Link
          href="/start"
          className="mt-6 inline-block bg-accent px-4 py-2 text-xs uppercase tracking-wider text-black"
        >
          Full runbook →
        </Link>
      </Section>
    </>
  );
}

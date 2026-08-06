import Link from "next/link";
import { Chip, Frame, Section, SectionHead } from "@/components/Shell";

export default function HomePage() {
  return (
    <>
      <Section className="border-b border-frame pt-16 md:pt-24">
        <div className="mb-6 inline-flex border border-frame">
          <span className="border-r border-frame bg-canvas px-3 py-2 text-[10px] uppercase tracking-wider text-ink">
            Built with DataHub
          </span>
          <span className="px-3 py-2 text-[10px] uppercase tracking-wider text-muted">
            Production ML Agents track
          </span>
        </div>
        <h1 className="max-w-4xl text-4xl font-medium leading-tight text-ink sm:text-5xl md:text-6xl">
          Catch silent ML breakage{" "}
          <span className="text-accent">before merge.</span>
        </h1>
        <p className="mt-6 max-w-2xl text-sm leading-relaxed text-muted opacity-90">
          Trueline is a production-ML guard agent. At pull-request time it walks
          DataHub&apos;s live lineage — training data → features → models →
          deployments — via MCP + SDK, and blocks silent degradation before it
          costs money.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/start"
            className="bg-accent px-5 py-2.5 text-xs uppercase tracking-wider text-black hover:brightness-110"
          >
            Run the guard
          </Link>
          <Link
            href="/guard"
            className="border border-frame px-5 py-2.5 text-xs uppercase tracking-wider text-ink hover:border-accent hover:text-accent"
          >
            How the guard works
          </Link>
          <a
            href="https://www.youtube.com"
            className="border border-frame px-5 py-2.5 text-xs uppercase tracking-wider text-muted hover:text-accent"
          >
            Watch on YouTube ↗
          </a>
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="The incident that never fired."
          desc="Production ML fails silently. The model doesn't crash — it degrades."
        />
        <Frame hot className="overflow-x-auto p-4 sm:p-6">
          <pre className="text-xs leading-relaxed text-muted sm:text-sm">
            <span className="text-accent">$</span> python scripts/run_local.py --base main --head demo/pr-2847 --pr 2847
            {"\n\n"}
            <span className="text-ink">  order_items.return_date</span>
            {"        "}DROP{"        "}author: @maya
            {"\n"}
            {"  column_suspects: return_date"}
            {"\n"}
            {"  └─ feature_order_risk          "}
            <span className="text-accent">MLFEATURE</span>
            {"\n"}
            {"  └─ fraud_model_v4              "}
            <span className="text-accent">MLMODEL</span>
            {"     [PROD] owner: @datahub"}
            {"\n"}
            {"  └─ fraud-scoring               "}
            <span className="text-accent">MLMODELGROUP</span>
            {"\n"}
            {"  └─ fraud-scoring-endpoint      "}
            <span className="text-accent">MLMODELDEPLOYMENT</span>
            {"\n\n"}
            {"  "}
            <Chip variant="critical">VERDICT CRITICAL</Chip>
            {"  dropping return_date reaches fraud_model_v4 [PROD]"}
          </pre>
        </Frame>
        <div className="mt-8 grid gap-0 border border-frame sm:grid-cols-3">
          {[
            {
              t: "The column disappears",
              d: "A drop or rename slips into training/feature input. No crash, no alert.",
            },
            {
              t: "The feature nulls",
              d: "Derived features degrade quietly and poison every prediction.",
            },
            {
              t: "The money leaks",
              d: "Teams spend weeks tracing what a PR-time lineage walk would have blocked.",
            },
          ].map((item) => (
            <div
              key={item.t}
              className="border-b border-frame p-5 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"
            >
              <div className="mb-3 h-1.5 w-1.5 bg-accent" />
              <h3 className="text-sm font-medium text-ink">{item.t}</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted">{item.d}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Three demo moments."
          desc="Same story the engine runs live — no canned severity."
        />
        <div className="grid gap-0 border border-frame md:grid-cols-3">
          {[
            {
              n: "01",
              t: "The red PR",
              d: "demo/pr-2847 drops return_date → CRITICAL on fraud_model_v4 + fraud-scoring-endpoint.",
              href: "/guard",
            },
            {
              n: "02",
              t: "Graph gets truer",
              d: "After merge, --commit --verify writes column lineage from the PR SQL.",
              href: "/lineage",
            },
            {
              n: "03",
              t: "Reviewed stamp",
              d: "Gated datasets get trueline.reviewed — the catalog records the agent walk.",
              href: "/lineage",
            },
          ].map((m) => (
            <Link
              key={m.n}
              href={m.href}
              className="border-b border-frame p-6 last:border-b-0 hover:bg-panel md:border-b-0 md:border-r md:last:border-r-0"
            >
              <p className="text-[10px] uppercase tracking-wider text-accent">{m.n}</p>
              <h3 className="mt-2 text-lg font-medium text-ink">{m.t}</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted">{m.d}</p>
            </Link>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame bg-band">
        <div className="divide-y divide-frame border border-frame">
          {[
            ["1", "merge gate — dry-run before, write-back after"],
            ["4", "severity tiers — CRITICAL · HIGH · MEDIUM · LOW"],
            ["2", "layers — guard the model, true the graph"],
            ["0", "invented lineage — facts from the engine only"],
          ].map(([n, c]) => (
            <div key={c} className="flex items-baseline gap-6 px-5 py-4">
              <span className="text-2xl text-accent sm:text-3xl">{n}</span>
              <span className="text-xs text-muted sm:text-sm">{c}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section className="bg-accent text-black">
        <h2 className="text-2xl font-medium sm:text-3xl md:text-4xl">
          Open a PR. Break nothing.
          <br />
          Catalog stays true.
        </h2>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/start"
            className="bg-black px-5 py-2.5 text-xs uppercase tracking-wider text-white hover:text-accent"
          >
            Start from the repo
          </Link>
          <Link
            href="/skill"
            className="border border-black px-5 py-2.5 text-xs uppercase tracking-wider text-black hover:bg-black hover:text-accent"
          >
            OSS skill
          </Link>
        </div>
      </Section>
    </>
  );
}

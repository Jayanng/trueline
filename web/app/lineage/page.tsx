import { Chip, Frame, PageHero, Section, SectionHead } from "@/components/Shell";

const PATH = [
  { id: "order_items", kind: "DATASET", note: "Training / feature input (demo tail)" },
  { id: "feature_order_risk", kind: "DATASET", note: "Feature table · table lineage only (column gap intentional)" },
  { id: "feature_order_risk", kind: "MLFEATURE", note: "sources=[feature dataset]" },
  { id: "fraud_model_v4", kind: "MLMODEL", note: "PROD · owner @datahub · mlFeatures + groups + deployments" },
  { id: "fraud-scoring", kind: "MLMODELGROUP", note: "Model group" },
  { id: "fraud-scoring-endpoint", kind: "MLMODELDEPLOYMENT", note: "Online endpoint — completes track path" },
];

export default function LineagePage() {
  return (
    <>
      <PageHero
        eyebrow="Page 03 · DataHub"
        title="ML lineage."
        desc="Training data → features → models → deployments. How Trueline reads and writes the live catalog — seed/, datahub_client.py, props.yaml."
      />

      <Section className="border-b border-frame">
        <SectionHead
          title="Full path (demo tail)"
          desc="showcase-ecommerce ships zero ML entities. seed/seed_ml_tail.py grafts real metadata via SDK emits."
        />
        <div className="border border-frame divide-y divide-frame">
          {PATH.map((n, i) => (
            <div
              key={`${n.id}-${n.kind}`}
              className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-center sm:gap-6"
            >
              <span className="text-[10px] text-accent">{String(i + 1).padStart(2, "0")}</span>
              <code className="text-sm text-ink">{n.id}</code>
              <Chip variant="lime">{n.kind}</Chip>
              <span className="text-xs text-muted sm:ml-auto">{n.note}</span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted">
          Honesty: demo entities, real SDK calls, labeled in seed/README.md and project README.
        </p>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Read path"
          desc="trueline/datahub_client.py — dual client for fidelity."
        />
        <div className="grid gap-0 border border-frame md:grid-cols-3">
          {[
            {
              t: "MCP",
              d: "get_lineage (upstream=False), search, get_entities — agent-facing tools on :8000",
            },
            {
              t: "GMS REST",
              d: "entitiesV2 aspects — mlFeatures, groups, deployments when MCP strips fields",
            },
            {
              t: "SDK lineage",
              d: "client.lineage.get_lineage multi-hop; reliable when MCP max_hops>2 is empty",
            },
          ].map((c) => (
            <div
              key={c.t}
              className="border-b border-frame p-5 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0"
            >
              <p className="text-xs uppercase tracking-wider text-accent">{c.t}</p>
              <p className="mt-2 text-xs leading-relaxed text-muted">{c.d}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Write path"
          desc="After merge only — PR is the approval gate."
        />
        <ul className="border border-frame divide-y divide-frame text-xs text-muted">
          <li className="px-4 py-3">
            <span className="text-ink">SDK add_lineage</span> — column mapping from PR SQL (
            <code>writeback.py</code>)
          </li>
          <li className="px-4 py-3">
            <span className="text-ink">Glossary terms</span> — optional PII propagation (
            <code>plan_term_drift</code>)
          </li>
          <li className="px-4 py-3">
            <span className="text-ink">trueline.reviewed</span> — structured property (
            <code>seed/props.yaml</code> + <code>stamp_reviewed</code>)
          </li>
          <li className="px-4 py-3">
            <span className="text-ink">SQLite journal</span> — PROPOSED / COMMITTED / SKIPPED (
            <code>state.py</code>)
          </li>
        </ul>
      </Section>

      <Section>
        <SectionHead
          title="Verify ground truth"
          desc="seed/verify_graph.py fails nonzero if the ML path is incomplete."
        />
        <Frame className="p-4">
          <pre className="text-xs text-muted">
            <span className="text-accent">$</span> python seed/seed_ml_tail.py{"\n"}
            <span className="text-accent">$</span> python seed/verify_graph.py{"\n"}
            <span className="text-ink">VERIFY OK</span> — feature → model → group → deployment
          </pre>
        </Frame>
      </Section>
    </>
  );
}

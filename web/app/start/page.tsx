import Link from "next/link";
import { Frame, PageHero, Section, SectionHead } from "@/components/Shell";

export default function StartPage() {
  return (
    <>
      <PageHero
        eyebrow="Page 05 · Runbook"
        title="Run it."
        desc="Reproduce the live guard from the repo. No video on this site — watch the ≤3 min walkthrough on YouTube when ready."
      />

      <Section className="border-b border-frame">
        <a
          href="https://www.youtube.com"
          className="flex items-center justify-between border border-frame px-4 py-3 text-xs uppercase tracking-wider text-muted hover:border-accent hover:text-accent"
        >
          <span>Watch the demo on YouTube</span>
          <span>↗</span>
        </a>
        <p className="mt-2 text-[10px] text-muted">
          External only — replace URL after upload. Nothing embeds here.
        </p>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="1 · DataHub + pack"
          desc="Docker is dev infrastructure only. Product itself is Docker-free."
        />
        <Frame className="p-4">
          <pre className="overflow-x-auto text-xs text-muted">
            pip install --upgrade acryl-datahub{"\n"}
            datahub docker quickstart{"\n"}
            datahub datapack load showcase-ecommerce{"\n"}
            # UI :9002 → Access Tokens → paste into .env
          </pre>
        </Frame>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="2 · Seed + verify ML tail"
          desc="seed/seed_ml_tail.py · seed/verify_graph.py"
        />
        <Frame className="p-4">
          <pre className="overflow-x-auto text-xs text-muted">
            python seed/seed_ml_tail.py{"\n"}
            # optional: datahub properties upsert -f seed/props.yaml{"\n"}
            python seed/verify_graph.py{"\n"}
            <span className="text-ink"># VERIFY OK — feature → model → group → deployment</span>
          </pre>
        </Frame>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="3 · Env"
          desc=".env.example — never commit secrets."
        />
        <Frame className="p-4">
          <pre className="overflow-x-auto text-xs text-muted">
            DATAHUB_GMS_URL=http://localhost:8080{"\n"}
            DATAHUB_GMS_TOKEN=…{"\n"}
            MCP_SERVER_URL=http://127.0.0.1:8000/mcp{"\n"}
            GMI_API_KEY=…              <span className="text-muted"># optional prose</span>
            {"\n"}
            GMI_MODEL=deepseek-ai/DeepSeek-V4-Flash{"\n"}
            TRUELINE_DRY_RUN=true
          </pre>
        </Frame>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="4 · MCP sidecar"
          desc="Must be up before lineage reads."
        />
        <Frame className="p-4">
          <pre className="text-xs text-muted">
            # example{"\n"}
            python -m mcp_server_datahub{"\n"}
            # listen http://127.0.0.1:8000/mcp
          </pre>
        </Frame>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="5 · Guard commands"
          desc="scripts/run_local.py · branches demo/pr-2847 and demo/pr-safe-add"
        />
        <div className="space-y-4">
          <Frame hot className="p-4">
            <p className="mb-2 text-[10px] uppercase tracking-wider text-accent">
              Red · CRITICAL
            </p>
            <pre className="overflow-x-auto text-xs text-muted">
              python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 \{"\n"}
              {"  --json .trueline/verdict.json --comment-out .trueline/comment.md \\"}{"\n"}
              {"  --notify-out .trueline/notify.json"}
            </pre>
          </Frame>
          <Frame className="p-4">
            <p className="mb-2 text-[10px] uppercase tracking-wider text-muted">
              Green · LOW
            </p>
            <pre className="overflow-x-auto text-xs text-muted">
              python scripts/run_local.py --repo . --base main --head demo/pr-safe-add --pr 2848
            </pre>
          </Frame>
          <Frame className="p-4">
            <p className="mb-2 text-[10px] uppercase tracking-wider text-muted">
              Shadow · exit 0
            </p>
            <pre className="overflow-x-auto text-xs text-muted">
              python scripts/run_local.py --repo . --base main --head demo/pr-2847 --pr 2847 --shadow
            </pre>
          </Frame>
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="6 · Tests + CI"
          desc="tests/ · .github/workflows/trueline.yml"
        />
        <Frame className="p-4">
          <pre className="text-xs text-muted">
            python -m pytest tests -k &quot;not e2e&quot; -q{"\n"}
            # Action: self-hosted (local quickstart not reachable from hosted runners)
          </pre>
        </Frame>
      </Section>

      <Section>
        <SectionHead
          title="Code map"
          desc="If it ships, it shows up on a page."
        />
        <div className="border border-frame divide-y divide-frame text-xs">
          {[
            ["trueline/", "/guard · /lineage"],
            ["scripts/run_local.py", "/guard · /start"],
            ["seed/", "/lineage · /start"],
            ["skill/datahub-pr-guard/", "/skill"],
            ["demo_repo/ + demo/* branches", "/guard · /start"],
            ["docs/DEVPOST.md · DEMO_SCRIPT.md", "submission (not site pages)"],
          ].map(([code, page]) => (
            <div key={code as string} className="grid gap-1 px-4 py-3 sm:grid-cols-2">
              <code className="text-accent">{code as string}</code>
              <span className="text-muted">{page as string}</span>
            </div>
          ))}
        </div>
        <Link
          href="/guard"
          className="mt-8 inline-block bg-accent px-4 py-2 text-xs uppercase tracking-wider text-black"
        >
          Back to the guard →
        </Link>
      </Section>
    </>
  );
}

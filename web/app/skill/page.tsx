import Link from "next/link";
import { Chip, Frame, PageHero, Section, SectionHead } from "@/components/Shell";

export default function SkillPage() {
  return (
    <>
      <PageHero
        eyebrow="Page 04 · OSS"
        title="datahub-pr-guard."
        desc="Non-interactive PR/CI skill for datahub-project/datahub-skills. Lives in skill/datahub-pr-guard/ — composes lineage + enrich with an ML severity model."
      />

      <Section className="border-b border-frame">
        <div className="mb-6 inline-flex border border-frame">
          <span className="border-r border-frame px-3 py-2 text-[10px] uppercase tracking-wider text-ink">
            OSS contribution
          </span>
          <span className="px-3 py-2 text-[10px] uppercase tracking-wider text-muted">
            datahub-skills
          </span>
        </div>
        <Frame className="p-4 sm:p-6">
          <pre className="overflow-x-auto text-xs leading-relaxed text-muted">
            <span className="text-accent">name:</span> datahub-pr-guard{"\n"}
            <span className="text-accent">description:</span> Non-interactive PR/CI gate…{"\n"}
            <span className="text-accent">user-invocable:</span> true{"\n"}
            <span className="text-accent">triggers:</span> &quot;gate this PR&quot; · &quot;what does this PR break&quot;
          </pre>
        </Frame>
        <p className="mt-3 text-xs text-muted">
          Source: <code className="text-ink">skill/datahub-pr-guard/SKILL.md</code>
        </p>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Not this skill"
          desc="Boundaries from SKILL.md — compose, don't rebuild."
        />
        <div className="border border-frame divide-y divide-frame text-xs">
          {[
            ["Explore lineage interactively", "datahub-lineage"],
            ["Enrich tags/terms ad hoc", "datahub-enrich"],
            ["Gate a PR on ML lineage + write-back plan", "datahub-pr-guard (this)"],
          ].map(([need, use]) => (
            <div key={need} className="grid gap-1 px-4 py-3 sm:grid-cols-2">
              <span className="text-muted">{need}</span>
              <code className="text-accent">{use}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Severity (skill reference)"
          desc="skill/datahub-pr-guard/references/severity-model.md"
        />
        <div className="border border-frame divide-y divide-frame">
          {[
            ["CRITICAL", "critical" as const, "Non-additive + ML downstream incl. deployment"],
            ["HIGH", "high" as const, "Dashboards / BI consumers"],
            ["MEDIUM", "medium" as const, "Multi-consumer or non-additive without ML"],
            ["LOW", "low" as const, "Additive only (green PR twin)"],
          ].map(([s, v, r]) => (
            <div key={s as string} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:gap-4">
              <Chip variant={v as "critical"}>{s as string}</Chip>
              <span className="text-xs text-muted">{r as string}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section className="border-b border-frame">
        <SectionHead
          title="Repo layout"
          desc="Everything under skill/datahub-pr-guard/"
        />
        <Frame className="p-4">
          <pre className="text-xs text-muted">
            skill/datahub-pr-guard/{"\n"}
            {"  SKILL.md\n"}
            {"  README.md\n"}
            {"  references/severity-model.md\n"}
            {"  templates/pr-verdict.template.md\n"}
            {"  tests/test_skill_anatomy.py"}
          </pre>
        </Frame>
      </Section>

      <Section>
        <SectionHead
          title="Principles"
          desc="Same contract as the Python engine."
        />
        <ul className="space-y-2 text-xs text-muted">
          <li>
            <span className="text-accent">·</span> Non-interactive — never prompts
          </li>
          <li>
            <span className="text-accent">·</span> Deterministic severity — LLM may phrase only
          </li>
          <li>
            <span className="text-accent">·</span> Idempotent write-backs — SKIPPED if already applied
          </li>
          <li>
            <span className="text-accent">·</span> Dry-run until merge — PR is the approval
          </li>
        </ul>
        <Link
          href="https://github.com/Jayanng/trueline/tree/main/skill/datahub-pr-guard"
          className="mt-8 inline-block border border-frame px-4 py-2 text-xs uppercase tracking-wider text-ink hover:border-accent hover:text-accent"
        >
          View skill on GitHub ↗
        </Link>
      </Section>
    </>
  );
}

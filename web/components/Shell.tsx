import Link from "next/link";
import { ReactNode } from "react";

const NAV = [
  { href: "/guard", label: "Guard" },
  { href: "/lineage", label: "Lineage" },
  { href: "/skill", label: "Skill" },
  { href: "/start", label: "Start" },
];

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-canvas text-ink font-mono">
      <header className="sticky top-0 z-50 border-b border-frame bg-canvas">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link
            href="/"
            className="text-sm font-medium uppercase tracking-wider text-ink hover:text-accent"
          >
            Trueline
          </Link>
          <nav className="flex flex-wrap items-center gap-1 sm:gap-2">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="px-2 py-1 text-[10px] uppercase tracking-wider text-muted hover:text-accent sm:px-3 sm:text-xs"
              >
                {item.label}
              </Link>
            ))}
            <a
              href="https://github.com/Jayanng/trueline"
              className="ml-1 border border-frame px-3 py-1.5 text-[10px] uppercase tracking-wider text-ink hover:border-accent hover:text-accent sm:text-xs"
            >
              GitHub
            </a>
            <Link
              href="/start"
              className="bg-accent px-3 py-1.5 text-[10px] uppercase tracking-wider text-black hover:brightness-110 sm:text-xs"
            >
              Run the guard
            </Link>
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="mt-auto border-t border-frame">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-4 sm:px-6">
          <div>
            <p className="text-xs uppercase tracking-wider text-ink">Trueline</p>
            <p className="mt-2 text-xs text-muted">
              Production ML Agents · DataHub MCP + SDK
            </p>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted">Product</p>
            <ul className="mt-2 space-y-1 text-xs">
              {NAV.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-ink hover:text-accent">
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted">Codebase</p>
            <ul className="mt-2 space-y-1 text-xs text-muted">
              <li>trueline/</li>
              <li>scripts/run_local.py</li>
              <li>seed/</li>
              <li>skill/datahub-pr-guard/</li>
            </ul>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-muted">External</p>
            <ul className="mt-2 space-y-1 text-xs">
              <li>
                <a
                  href="https://github.com/Jayanng/trueline"
                  className="text-ink hover:text-accent"
                >
                  GitHub repo
                </a>
              </li>
              <li>
                <a
                  href="https://www.youtube.com"
                  className="text-ink hover:text-accent"
                >
                  Demo on YouTube
                </a>
              </li>
              <li>
                <a
                  href="https://datahubproject.io"
                  className="text-ink hover:text-accent"
                >
                  DataHub
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-frame px-4 py-3 text-center text-[10px] text-muted sm:px-6">
          Apache 2.0 · Catalog stays true · No in-site video — demo on YouTube
        </div>
      </footer>
    </div>
  );
}

export function Section({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`w-full px-4 py-12 sm:px-6 sm:py-16 md:px-8 ${className}`}>
      <div className="mx-auto max-w-6xl">{children}</div>
    </section>
  );
}

export function SectionHead({
  title,
  desc,
}: {
  title: string;
  desc: string;
}) {
  return (
    <div className="mb-8 flex flex-col gap-3">
      <h2 className="text-2xl font-medium text-ink sm:text-3xl md:text-4xl">{title}</h2>
      <p className="max-w-2xl text-sm text-muted opacity-80">{desc}</p>
    </div>
  );
}

export function Frame({
  children,
  className = "",
  hot = false,
}: {
  children: ReactNode;
  className?: string;
  hot?: boolean;
}) {
  return (
    <div
      className={`border bg-panel ${hot ? "border-accent" : "border-frame"} ${className}`}
    >
      {children}
    </div>
  );
}

export function Chip({
  children,
  variant = "muted",
}: {
  children: ReactNode;
  variant?: "critical" | "high" | "medium" | "low" | "muted" | "lime";
}) {
  const styles: Record<string, string> = {
    critical: "bg-accent text-black",
    high: "border border-ink text-ink",
    medium: "border border-frame text-muted",
    low: "text-muted",
    muted: "border border-frame text-muted",
    lime: "bg-accent text-black",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 text-[10px] uppercase tracking-wider ${styles[variant]}`}
    >
      {children}
    </span>
  );
}

export function PageHero({
  eyebrow,
  title,
  desc,
}: {
  eyebrow: string;
  title: string;
  desc: string;
}) {
  return (
    <Section className="border-b border-frame pt-16 md:pt-20">
      <p className="mb-3 text-[10px] uppercase tracking-wider text-accent">{eyebrow}</p>
      <h1 className="max-w-3xl text-3xl font-medium text-ink sm:text-4xl md:text-5xl">
        {title}
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-muted opacity-80">{desc}</p>
    </Section>
  );
}

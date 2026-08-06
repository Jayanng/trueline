import Link from "next/link";
import { Frame, Section } from "@/components/Shell";

export default function NotFound() {
  return (
    <Section className="pt-24">
      <Frame className="p-6">
        <pre className="text-sm text-muted">
          <span className="text-accent">$</span> trueline --route /unknown{"\n"}
          exit code 404 — no such route. catalog stays true.
        </pre>
      </Frame>
      <Link
        href="/"
        className="mt-6 inline-block bg-accent px-4 py-2 text-xs uppercase tracking-wider text-black"
      >
        Back home
      </Link>
    </Section>
  );
}

import type { Metadata } from "next";
import "./globals.css";
import { Shell } from "@/components/Shell";

export const metadata: Metadata = {
  title: "Trueline — Gate PRs on DataHub ML lineage",
  description:
    "Production ML Agents guard: silent model breakage dies in review. MCP + SDK on live DataHub lineage.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}

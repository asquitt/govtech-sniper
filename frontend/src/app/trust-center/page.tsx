import Link from "next/link";

const guarantees = [
  "Customer proposal content is never used to train third-party AI models",
  "AI processing runs in ephemeral request mode with retention boundaries",
  "Tenant data remains logically isolated with RBAC and audit controls",
  "All data is encrypted in transit (TLS 1.3) and at rest (AES-256)",
  "Human review gates are available before submission workflows",
];

const boundaries = [
  {
    title: "Model behavior controls",
    detail:
      "AI calls are restricted by runtime governance policies that fail closed if no-training guarantees drift.",
  },
  {
    title: "Retention boundaries",
    detail:
      "Prompt/output retention controls are configurable per organization with transparent policy visibility.",
  },
  {
    title: "Auditability",
    detail:
      "Security-relevant actions (exports, policy changes, access events) are recorded in audit logs.",
  },
  {
    title: "Enterprise governance",
    detail:
      "Organization admins can control AI usage for analysis/drafting and enforce human review requirements.",
  },
];

export default function TrustCenterPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-6 py-16 space-y-10">
        <header className="space-y-4">
          <p className="text-xs uppercase tracking-[0.22em] text-primary">RFP Sniper Trust Center</p>
          <h1 className="text-4xl font-bold tracking-tight">Data Isolation and AI Usage Guarantees</h1>
          <p className="text-muted-foreground max-w-3xl">
            This page describes how proposal and solicitation data is handled, where it is stored,
            and the technical/runtime controls that enforce our no-training guarantee.
          </p>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/privacy"
              className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm"
            >
              Privacy Policy
            </Link>
            <Link
              href="/compliance"
              className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm"
            >
              Compliance Dashboard
            </Link>
          </div>
        </header>

        <section className="rounded-xl border border-border bg-card p-6 space-y-4">
          <h2 className="text-xl font-semibold">Core Guarantees</h2>
          <ul className="space-y-2">
            {guarantees.map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm text-muted-foreground">
                <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary" />
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {boundaries.map((item) => (
            <article key={item.title} className="rounded-xl border border-border bg-card p-5 space-y-2">
              <h3 className="text-base font-semibold">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.detail}</p>
            </article>
          ))}
        </section>

        <section className="rounded-xl border border-border bg-card p-6 space-y-3">
          <h2 className="text-xl font-semibold">Security Contact</h2>
          <p className="text-sm text-muted-foreground">
            For security reviews, data processing agreements, or enterprise assurance requests,
            contact <a href="mailto:security@rfpsniper.com" className="text-primary underline">security@rfpsniper.com</a>.
          </p>
          <p className="text-xs text-muted-foreground">Last updated: February 14, 2026</p>
        </section>
      </div>
    </div>
  );
}

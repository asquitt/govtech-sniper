import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-6 py-16 space-y-8">
        <div>
          <h1 className="text-3xl font-bold">Privacy Policy</h1>
          <p className="text-muted-foreground mt-2">Last updated: February 2026</p>
          <div className="mt-3">
            <Link
              href="/trust-center"
              className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm"
            >
              View Trust Center
            </Link>
          </div>
        </div>

        <Section title="1. Information We Collect">
          <p>
            RFP Sniper collects information you provide when creating an account, uploading
            documents, and using our proposal generation features. This includes your name,
            email address, organization details, and uploaded solicitation documents.
          </p>
        </Section>

        <Section title="2. How We Use Your Information">
          <ul className="list-disc pl-5 space-y-1">
            <li>Provide, maintain, and improve our proposal automation services</li>
            <li>Analyze solicitation documents to extract compliance requirements</li>
            <li>Generate proposal drafts using AI-powered writing assistance</li>
            <li>Send notifications about deadlines and system updates</li>
            <li>Ensure platform security and prevent unauthorized access</li>
          </ul>
        </Section>

        <Section title="3. Data Storage and Security">
          <p>
            All data is stored in encrypted databases with AES-256 encryption at rest.
            Communications are protected with TLS 1.3. We implement role-based access
            controls, audit logging, and regular security assessments aligned with
            NIST 800-53 and CMMC Level 2 frameworks.
          </p>
        </Section>

        <Section title="4. Data Sharing">
          <p>
            We do not sell or share your personal information or proposal content with
            third-party advertisers. Data may be shared with infrastructure providers
            (cloud hosting, AI model providers) solely for service delivery, under
            strict data processing agreements.
          </p>
        </Section>

        <Section title="5. Data Retention">
          <ul className="list-disc pl-5 space-y-1">
            <li>Active account data is retained for the lifetime of your account</li>
            <li>Deleted proposals are purged after a 30-day grace period</li>
            <li>Audit logs are retained for 7 years per compliance requirements</li>
            <li>Account deletion requests are fulfilled within 30 days</li>
          </ul>
        </Section>

        <Section title="6. Your Rights">
          <p>
            You have the right to access, correct, or delete your personal data. You may
            export your proposal data at any time. To exercise these rights, contact us at
            privacy@rfpsniper.com.
          </p>
        </Section>

        <Section title="7. Compliance">
          <p>
            RFP Sniper maintains compliance with applicable federal data handling
            requirements, including CUI-level protections. We pursue SOC 2 Type II
            certification and FedRAMP readiness to serve government contractors
            with confidence.
          </p>
        </Section>

        <Section title="8. Contact">
          <p>
            For questions about this privacy policy, contact us at privacy@rfpsniper.com.
          </p>
        </Section>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed">{children}</div>
    </section>
  );
}

export default function AIDataPrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-3xl font-bold tracking-tight mb-2">
        AI & Data Privacy
      </h1>
      <p className="text-muted-foreground mb-8">
        How Orbitr handles your data with AI services
      </p>

      <div className="space-y-8">
        <section>
          <h2 className="text-xl font-semibold mb-3">
            Your Data Is Never Used to Train AI Models
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Orbitr uses Google Gemini API in ephemeral mode for all AI operations.
            Your proposals, RFPs, knowledge base documents, and compliance matrices
            are processed for your request only and are never retained by the AI
            provider for model training or improvement purposes.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">
            Data Processing Guarantees
          </h2>
          <ul className="space-y-3 text-muted-foreground">
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>All AI API calls use ephemeral processing — no data retention by the AI provider</span>
            </li>
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>Your documents are encrypted at rest (AES-256) and in transit (TLS 1.3)</span>
            </li>
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>Knowledge base embeddings are stored in your isolated database, not shared</span>
            </li>
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>Audit logs track every AI operation with timestamps and user attribution</span>
            </li>
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>No customer data is used for model training, fine-tuning, or evaluation</span>
            </li>
            <li className="flex gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span>Data residency within the United States for all storage and processing</span>
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">
            Security Certifications
          </h2>
          <p className="text-muted-foreground leading-relaxed mb-4">
            We are actively pursuing industry-standard security certifications
            to meet the requirements of defense and government contractors.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-lg border p-4">
              <h3 className="font-medium mb-1">FedRAMP Moderate</h3>
              <p className="text-sm text-muted-foreground">SSP in preparation — targeting Q4 2026 submission</p>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-medium mb-1">CMMC Level 2</h3>
              <p className="text-sm text-muted-foreground">Self-assessment in progress — targeting Q3 2026</p>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-medium mb-1">SOC 2 Type II</h3>
              <p className="text-sm text-muted-foreground">Controls documentation started — targeting 2027</p>
            </div>
            <div className="rounded-lg border p-4">
              <h3 className="font-medium mb-1">NIST 800-171</h3>
              <p className="text-sm text-muted-foreground">Controls aligned — documentation in progress</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold mb-3">
            Questions?
          </h2>
          <p className="text-muted-foreground">
            Contact our security team at{" "}
            <a href="mailto:security@orbitr.io" className="text-primary hover:underline">
              security@orbitr.io
            </a>{" "}
            for security assessments, data processing agreements, or compliance documentation.
          </p>
        </section>
      </div>
    </div>
  );
}

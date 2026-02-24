"use client";

interface OrgBootstrapFormProps {
  name: string;
  slug: string;
  domain: string;
  billingEmail: string;
  submitting: boolean;
  error: string | null;
  onNameChange: (value: string) => void;
  onSlugChange: (value: string) => void;
  onDomainChange: (value: string) => void;
  onBillingEmailChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  toSlug: (value: string) => string;
}

export function OrgBootstrapForm({
  name,
  slug,
  domain,
  billingEmail,
  submitting,
  error,
  onNameChange,
  onSlugChange,
  onDomainChange,
  onBillingEmailChange,
  onSubmit,
  toSlug,
}: OrgBootstrapFormProps) {
  return (
    <div className="flex-1 p-6 overflow-auto">
      <div className="mx-auto max-w-xl rounded-lg border border-border p-5 space-y-4">
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">Set up your organization</p>
          <p className="text-xs text-muted-foreground">
            Create an organization to enable admin access, member management, and audit logs.
          </p>
        </div>

        <form className="space-y-3" onSubmit={onSubmit}>
          <div className="space-y-1">
            <label
              htmlFor="bootstrap-org-name"
              className="text-xs text-muted-foreground"
            >
              Organization name
            </label>
            <input
              id="bootstrap-org-name"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder="Acme GovTech"
              value={name}
              onChange={(event) => {
                const value = event.target.value;
                onNameChange(value);
                if (!slug) {
                  onSlugChange(toSlug(value));
                }
              }}
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="bootstrap-org-slug"
              className="text-xs text-muted-foreground"
            >
              Organization slug
            </label>
            <input
              id="bootstrap-org-slug"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder="acme-govtech"
              value={slug}
              onChange={(event) => onSlugChange(toSlug(event.target.value))}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label
                htmlFor="bootstrap-org-domain"
                className="text-xs text-muted-foreground"
              >
                Domain (optional)
              </label>
              <input
                id="bootstrap-org-domain"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                placeholder="acme.com"
                value={domain}
                onChange={(event) => onDomainChange(event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label
                htmlFor="bootstrap-org-billing-email"
                className="text-xs text-muted-foreground"
              >
                Billing email (optional)
              </label>
              <input
                id="bootstrap-org-billing-email"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                placeholder="billing@acme.com"
                value={billingEmail}
                onChange={(event) => onBillingEmailChange(event.target.value)}
              />
            </div>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}

          <button
            type="submit"
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
            disabled={submitting}
          >
            {submitting ? "Creating..." : "Create Organization"}
          </button>
        </form>
      </div>
    </div>
  );
}

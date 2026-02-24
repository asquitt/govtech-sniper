"use client";

import type { OrganizationDetails } from "@/types";

type OrgSecurityPolicyKey =
  | "require_step_up_for_sensitive_exports"
  | "require_step_up_for_sensitive_shares"
  | "apply_cui_watermark_to_sensitive_exports"
  | "apply_cui_redaction_to_sensitive_exports";

interface SecurityControlsCardProps {
  org: OrganizationDetails | null;
  loading: boolean;
  policySaving: OrgSecurityPolicyKey | null;
  policyError: string | null;
  onPolicyToggle: (key: OrgSecurityPolicyKey, enabled: boolean) => void;
}

const POLICY_CONTROLS: {
  key: OrgSecurityPolicyKey;
  label: string;
  description: string;
  ariaLabel: string;
  defaultChecked: boolean;
}[] = [
  {
    key: "require_step_up_for_sensitive_exports",
    label: "Sensitive exports require step-up",
    description: "Applies to policy-gated proposal exports and collaboration audit exports.",
    ariaLabel: "Sensitive exports step-up toggle",
    defaultChecked: true,
  },
  {
    key: "require_step_up_for_sensitive_shares",
    label: "Sensitive shares require step-up",
    description: "Applies to sensitive workspace share operations and preset application.",
    ariaLabel: "Sensitive shares step-up toggle",
    defaultChecked: true,
  },
  {
    key: "apply_cui_watermark_to_sensitive_exports",
    label: "Apply CUI watermark to sensitive exports",
    description: "Adds classification handling notice artifacts to CUI compliance packages.",
    ariaLabel: "CUI watermark toggle",
    defaultChecked: true,
  },
  {
    key: "apply_cui_redaction_to_sensitive_exports",
    label: "Apply CUI redaction to sensitive exports",
    description: "Redacts sensitive evidence metadata from CUI package source-trace outputs.",
    ariaLabel: "CUI redaction toggle",
    defaultChecked: false,
  },
];

export function SecurityControlsCard({
  org,
  loading,
  policySaving,
  policyError,
  onPolicyToggle,
}: SecurityControlsCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-3">
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Security Controls</p>
        <p className="text-xs text-muted-foreground">
          Configure step-up authentication for sensitive collaboration and export actions.
        </p>
      </div>
      {POLICY_CONTROLS.map((control) => (
        <label
          key={control.key}
          className="flex items-start justify-between gap-3 rounded-md border border-border px-3 py-2"
        >
          <div className="space-y-1">
            <p className="text-sm text-foreground">{control.label}</p>
            <p className="text-xs text-muted-foreground">{control.description}</p>
          </div>
          <input
            aria-label={control.ariaLabel}
            type="checkbox"
            checked={org?.[control.key] ?? control.defaultChecked}
            disabled={loading || policySaving !== null}
            onChange={(event) => onPolicyToggle(control.key, event.target.checked)}
          />
        </label>
      ))}
      {policyError ? <p className="text-xs text-destructive">{policyError}</p> : null}
    </div>
  );
}

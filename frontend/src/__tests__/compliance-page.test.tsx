import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import CompliancePage from "@/app/(dashboard)/compliance/page";
import { complianceApi } from "@/lib/api/compliance";

vi.mock("@/lib/api/compliance", () => ({
  complianceApi: {
    getCMMCStatus: vi.fn(),
    getNISTOverview: vi.fn(),
    getDataPrivacy: vi.fn(),
    getComplianceAuditSummary: vi.fn(),
    getReadiness: vi.fn(),
    getTrustCenter: vi.fn(),
    updateTrustCenterPolicy: vi.fn(),
    exportTrustCenterEvidence: vi.fn(),
  },
}));

const mockedComplianceApi = vi.mocked(complianceApi);

const baseTrustCenter = {
  organization_id: 7,
  organization_name: "Acme Gov",
  can_manage_policy: true,
  policy: {
    allow_ai_requirement_analysis: true,
    allow_ai_draft_generation: true,
    require_human_review_for_submission: true,
    share_anonymized_product_telemetry: false,
    retain_prompt_logs_days: 0,
    retain_output_logs_days: 30,
  },
  runtime_guarantees: {
    model_provider: "Google Gemini API",
    processing_mode: "ephemeral_no_training",
    provider_training_allowed: false,
    provider_retention_hours: 0,
    no_training_enforced: true,
  },
  evidence: [
    {
      control: "Provider model training",
      status: "enforced" as const,
      detail: "Gemini processing runs in ephemeral no-training mode.",
    },
  ],
  updated_at: "2026-02-14T12:00:00Z",
};

describe("CompliancePage", () => {
  beforeEach(() => {
    mockedComplianceApi.getCMMCStatus.mockResolvedValue({
      total_controls: 10,
      met_controls: 8,
      score_percentage: 80,
      target_level: 2,
      domains: [
        {
          domain: "AC",
          domain_name: "Access Control",
          total_controls: 5,
          met_controls: 4,
          percentage: 80,
        },
      ],
    });
    mockedComplianceApi.getNISTOverview.mockResolvedValue({
      framework: "NIST 800-53 Rev 5",
      total_families: 1,
      overall_coverage: 75,
      families: [
        {
          family_id: "AC",
          name: "Access Control",
          total_controls: 10,
          implemented: 7,
          partial: 2,
          not_implemented: 1,
        },
      ],
    });
    mockedComplianceApi.getDataPrivacy.mockResolvedValue({
      data_handling: ["No training usage"],
      encryption: ["AES-256"],
      access_controls: ["RBAC"],
      data_retention: ["30 day grace"],
      certifications: ["CMMC Level 2"],
    });
    mockedComplianceApi.getComplianceAuditSummary.mockResolvedValue({
      total_events: 20,
      events_last_30_days: 8,
      by_type: { "compliance.trust_policy.updated": 1 },
      compliance_score: 79,
    });
    mockedComplianceApi.getReadiness.mockResolvedValue({
      programs: [
        {
          id: "cmmc_level_2",
          name: "CMMC Level 2",
          status: "in_progress",
          percent_complete: 80,
          next_milestone: "External assessor packet",
        },
      ],
      last_updated: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.getTrustCenter.mockResolvedValue(baseTrustCenter);
    mockedComplianceApi.updateTrustCenterPolicy.mockResolvedValue(baseTrustCenter);
    mockedComplianceApi.exportTrustCenterEvidence.mockResolvedValue(
      new Blob([JSON.stringify({ ok: true })], { type: "application/json" })
    );
  });

  it("renders trust center controls in read-only mode for non-admin users", async () => {
    mockedComplianceApi.getTrustCenter.mockResolvedValueOnce({
      ...baseTrustCenter,
      can_manage_policy: false,
      organization_id: null,
      organization_name: null,
    });

    render(<CompliancePage />);

    expect(await screen.findByText("AI & Data Trust Center")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Visibility is enabled for all users. Organization owners/admins can edit these controls."
      )
    ).toBeInTheDocument();
    expect(screen.getByLabelText("AI requirement analysis toggle")).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: "Save policy controls" })
    ).not.toBeInTheDocument();
  });

  it("updates trust center policy controls for admins", async () => {
    mockedComplianceApi.updateTrustCenterPolicy.mockResolvedValueOnce({
      ...baseTrustCenter,
      policy: {
        ...baseTrustCenter.policy,
        allow_ai_requirement_analysis: false,
      },
      updated_at: "2026-02-14T12:15:00Z",
    });

    render(<CompliancePage />);

    expect(await screen.findByText("AI & Data Trust Center")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("AI requirement analysis toggle"));
    fireEvent.click(screen.getByRole("button", { name: "Save policy controls" }));

    await waitFor(() => {
      expect(mockedComplianceApi.updateTrustCenterPolicy).toHaveBeenCalledWith(
        expect.objectContaining({
          allow_ai_requirement_analysis: false,
          allow_ai_draft_generation: true,
          require_human_review_for_submission: true,
        })
      );
    });

    expect(await screen.findByText("Trust center policy saved.")).toBeInTheDocument();
  });
});

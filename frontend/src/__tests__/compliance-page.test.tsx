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
    getReadinessCheckpoints: vi.fn(),
    getTrustMetrics: vi.fn(),
    getGovCloudProfile: vi.fn(),
    getSOC2Readiness: vi.fn(),
    getTrustCenter: vi.fn(),
    updateTrustCenterPolicy: vi.fn(),
    exportTrustCenterEvidenceWithOptions: vi.fn(),
    exportThreePAOPackage: vi.fn(),
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
    mockedComplianceApi.getReadinessCheckpoints.mockResolvedValue({
      checkpoints: [
        {
          checkpoint_id: "fedramp_3pao_readiness",
          program_id: "fedramp_moderate",
          title: "3PAO readiness checkpoint and assessor onboarding",
          status: "scheduled",
          target_date: "2026-05-20T00:00:00Z",
          owner: "Compliance Lead",
          third_party_required: true,
          evidence_items_ready: 9,
          evidence_items_total: 24,
          evidence_source: "registry",
          evidence_last_updated_at: "2026-02-14T10:00:00Z",
          assessor_signoff_status: "approved",
          assessor_signoff_by: "Accredited 3PAO",
          assessor_signed_at: "2026-02-14T10:30:00Z",
        },
      ],
      generated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.getTrustMetrics.mockResolvedValue({
      generated_at: "2026-02-14T12:00:00Z",
      window_days: 30,
      checkpoint_evidence_completeness_rate: 68.2,
      checkpoint_signoff_completion_rate: 40,
      trust_export_success_rate_30d: 95,
      trust_export_successes_30d: 19,
      trust_export_failures_30d: 1,
      step_up_challenge_success_rate_30d: 83.3,
      step_up_challenge_successes_30d: 5,
      step_up_challenge_failures_30d: 1,
      trust_ci_pass_rate_30d: null,
    });
    mockedComplianceApi.getGovCloudProfile.mockResolvedValue({
      program_id: "govcloud_deployment",
      provider: "AWS GovCloud (US)",
      status: "in_progress",
      target_regions: ["us-gov-west-1", "us-gov-east-1"],
      boundary_services: ["Amazon EKS (GovCloud)", "Amazon RDS PostgreSQL"],
      identity_federation_status: "in_progress",
      network_isolation_status: "validated_in_preprod",
      data_residency_status: "us_government_regions_only",
      migration_phases: [
        {
          phase_id: "identity_cutover",
          title: "SSO federation and privileged access cutover",
          status: "in_progress",
          target_date: "2026-04-12T00:00:00Z",
          owner: "Identity & Access Lead",
          exit_criteria: [
            "IdP federation mapped to GovCloud IAM Identity Center",
          ],
        },
      ],
      updated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.getSOC2Readiness.mockResolvedValue({
      program_id: "soc2_type_ii",
      name: "SOC 2 Type II",
      status: "in_progress",
      audit_firm_status: "engagement_letter_signed",
      observation_window_start: "2026-03-01T00:00:00Z",
      observation_window_end: "2026-08-31T00:00:00Z",
      overall_percent_complete: 68,
      domains: [
        {
          domain_id: "CC1",
          domain_name: "Control Environment",
          controls_total: 18,
          controls_ready: 13,
          percent_complete: 72,
          owner: "Security Program Manager",
        },
      ],
      milestones: [
        {
          milestone_id: "auditor_kickoff",
          title: "External auditor kickoff and PBC package lock",
          status: "scheduled",
          due_date: "2026-05-05T00:00:00Z",
          owner: "Compliance Lead",
          evidence_ready: false,
          notes: "Awaiting final access review exports.",
        },
      ],
      updated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.getTrustCenter.mockResolvedValue(baseTrustCenter);
    mockedComplianceApi.updateTrustCenterPolicy.mockResolvedValue(baseTrustCenter);
    mockedComplianceApi.exportTrustCenterEvidenceWithOptions.mockResolvedValue(
      new Blob([JSON.stringify({ ok: true })], { type: "application/json" })
    );
    mockedComplianceApi.exportThreePAOPackage.mockResolvedValue(
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

  it("renders SOC 2 execution track details", async () => {
    render(<CompliancePage />);
    expect(await screen.findByText("SOC 2 Type II Execution Track")).toBeInTheDocument();
    expect(screen.getByText("engagement letter signed")).toBeInTheDocument();
    expect(screen.getByText("Trust Criteria Domains")).toBeInTheDocument();
    expect(screen.getByText("Milestones")).toBeInTheDocument();
    expect(
      screen.getByText("External auditor kickoff and PBC package lock")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Execution Checkpoints (FedRAMP, CMMC, GovCloud)")
    ).toBeInTheDocument();
    expect(
      screen.getByText("3PAO readiness checkpoint and assessor onboarding")
    ).toBeInTheDocument();
    expect(screen.getByText("Evidence completeness")).toBeInTheDocument();
    expect(screen.getByText("68.2%")).toBeInTheDocument();
    expect(screen.getByText("Source: registry")).toBeInTheDocument();
    expect(screen.getByText("Assessor sign-off: approved")).toBeInTheDocument();
    expect(screen.getByText("Assessor: Accredited 3PAO")).toBeInTheDocument();
    expect(screen.getByText("GovCloud Deployment Profile")).toBeInTheDocument();
    expect(screen.getByText("SSO federation and privileged access cutover")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export 3PAO Readiness Package" })).toBeInTheDocument();
  });

  it("exports trust evidence using selected format and signed options", async () => {
    render(<CompliancePage />);
    expect(await screen.findByText("AI & Data Trust Center")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Trust export format"), {
      target: { value: "csv" },
    });
    fireEvent.click(screen.getByLabelText("Signed trust export toggle"));
    fireEvent.click(screen.getByRole("button", { name: "Export Trust Evidence" }));

    await waitFor(() => {
      expect(mockedComplianceApi.exportTrustCenterEvidenceWithOptions).toHaveBeenCalledWith({
        format: "csv",
        signed: true,
      });
    });
  });

  it("exports the 3PAO readiness package", async () => {
    render(<CompliancePage />);
    expect(await screen.findByText("AI & Data Trust Center")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Export 3PAO Readiness Package" }));

    await waitFor(() => {
      expect(mockedComplianceApi.exportThreePAOPackage).toHaveBeenCalledTimes(1);
    });
  });
});

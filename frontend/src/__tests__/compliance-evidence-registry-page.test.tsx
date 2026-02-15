import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import ComplianceEvidenceRegistryPage from "@/app/(dashboard)/compliance/evidence-registry/page";
import { complianceApi } from "@/lib/api/compliance";

vi.mock("@/lib/api/compliance", () => ({
  complianceApi: {
    getReadinessCheckpoints: vi.fn(),
    getTrustCenter: vi.fn(),
    listCheckpointEvidence: vi.fn(),
    getCheckpointSignoff: vi.fn(),
    listRegistryEvidence: vi.fn(),
    createCheckpointEvidence: vi.fn(),
    updateCheckpointEvidence: vi.fn(),
    upsertCheckpointSignoff: vi.fn(),
  },
}));

const mockedComplianceApi = vi.mocked(complianceApi);

describe("ComplianceEvidenceRegistryPage", () => {
  beforeEach(() => {
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
          evidence_items_ready: 1,
          evidence_items_total: 3,
          evidence_source: "registry",
          evidence_last_updated_at: "2026-02-14T10:00:00Z",
          assessor_signoff_status: "pending",
          assessor_signoff_by: null,
          assessor_signed_at: null,
        },
      ],
      generated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.getTrustCenter.mockResolvedValue({
      organization_id: 12,
      organization_name: "Trust Org",
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
      evidence: [],
      updated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.listCheckpointEvidence.mockResolvedValue([]);
    mockedComplianceApi.getCheckpointSignoff.mockResolvedValue({
      checkpoint_id: "fedramp_3pao_readiness",
      status: "pending",
      assessor_name: "Pending assessor assignment",
      assessor_org: null,
      notes: null,
      signed_by_user_id: null,
      signed_at: null,
      updated_at: "2026-02-14T12:00:00Z",
    });
    mockedComplianceApi.listRegistryEvidence.mockResolvedValue([
      {
        id: 88,
        user_id: 1,
        title: "IAM workflow screenshot",
        evidence_type: "screenshot",
        description: "Provisioning control evidence",
        file_path: null,
        url: null,
        collected_at: "2026-02-10T11:00:00Z",
        expires_at: null,
        created_at: "2026-02-10T11:00:00Z",
        updated_at: "2026-02-10T11:00:00Z",
      },
    ]);
    mockedComplianceApi.createCheckpointEvidence.mockResolvedValue({
      link_id: 501,
      checkpoint_id: "fedramp_3pao_readiness",
      evidence_id: 88,
      title: "IAM workflow screenshot",
      evidence_type: "screenshot",
      description: "Provisioning control evidence",
      file_path: null,
      url: null,
      collected_at: "2026-02-10T11:00:00Z",
      expires_at: null,
      status: "submitted",
      notes: "Mapped to checkpoint",
      reviewer_user_id: null,
      reviewer_notes: null,
      reviewed_at: null,
      linked_at: "2026-02-14T12:10:00Z",
    });
    mockedComplianceApi.updateCheckpointEvidence.mockResolvedValue({
      link_id: 501,
      checkpoint_id: "fedramp_3pao_readiness",
      evidence_id: 88,
      title: "IAM workflow screenshot",
      evidence_type: "screenshot",
      description: "Provisioning control evidence",
      file_path: null,
      url: null,
      collected_at: "2026-02-10T11:00:00Z",
      expires_at: null,
      status: "accepted",
      notes: "Mapped to checkpoint",
      reviewer_user_id: 1,
      reviewer_notes: "Looks good",
      reviewed_at: "2026-02-14T12:12:00Z",
      linked_at: "2026-02-14T12:10:00Z",
    });
    mockedComplianceApi.upsertCheckpointSignoff.mockResolvedValue({
      checkpoint_id: "fedramp_3pao_readiness",
      status: "approved",
      assessor_name: "Accredited 3PAO",
      assessor_org: "Assessors LLC",
      notes: "Ready for review",
      signed_by_user_id: 1,
      signed_at: "2026-02-14T12:15:00Z",
      updated_at: "2026-02-14T12:15:00Z",
    });
  });

  it("loads organization evidence scope and links selected evidence", async () => {
    render(<ComplianceEvidenceRegistryPage />);

    expect(await screen.findByText("Evidence Links")).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedComplianceApi.listRegistryEvidence).toHaveBeenCalledWith({
        scope: "organization",
        limit: 200,
      });
    });

    fireEvent.change(screen.getByLabelText("Evidence notes"), {
      target: { value: "Mapped to checkpoint" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Link Evidence" }));

    await waitFor(() => {
      expect(mockedComplianceApi.createCheckpointEvidence).toHaveBeenCalledWith(
        "fedramp_3pao_readiness",
        {
          evidence_id: 88,
          notes: "Mapped to checkpoint",
        }
      );
    });

    fireEvent.change(screen.getByLabelText("Evidence scope"), {
      target: { value: "mine" },
    });

    await waitFor(() => {
      expect(mockedComplianceApi.listRegistryEvidence).toHaveBeenCalledWith({
        scope: "mine",
        limit: 200,
      });
    });
  });
});

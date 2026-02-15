import api from "./client";
import type {
  CMMCStatus,
  ComplianceCheckpointEvidenceCreate,
  ComplianceCheckpointEvidenceItem,
  ComplianceCheckpointEvidenceUpdate,
  ComplianceCheckpointSignoff,
  ComplianceCheckpointSignoffWrite,
  ComplianceRegistryEvidenceItem,
  ComplianceTrustMetrics,
  NISTOverview,
  DataPrivacyInfo,
  ComplianceAuditSummary,
  ComplianceReadiness,
  ComplianceReadinessCheckpointSnapshot,
  GovCloudDeploymentProfile,
  SOC2Readiness,
  TrustCenterPolicyUpdate,
  TrustCenterProfile,
} from "@/types/compliance";

export const complianceApi = {
  getNISTOverview: async (): Promise<NISTOverview> => {
    const { data } = await api.get("/compliance/overview");
    return data;
  },

  getCMMCStatus: async (): Promise<CMMCStatus> => {
    const { data } = await api.get("/compliance/cmmc-status");
    return data;
  },

  getDataPrivacy: async (): Promise<DataPrivacyInfo> => {
    const { data } = await api.get("/compliance/data-privacy");
    return data;
  },

  getComplianceAuditSummary: async (): Promise<ComplianceAuditSummary> => {
    const { data } = await api.get("/compliance/audit-summary");
    return data;
  },

  getReadiness: async (): Promise<ComplianceReadiness> => {
    const { data } = await api.get("/compliance/readiness");
    return data;
  },

  getSOC2Readiness: async (): Promise<SOC2Readiness> => {
    const { data } = await api.get("/compliance/soc2-readiness");
    return data;
  },

  getReadinessCheckpoints: async (): Promise<ComplianceReadinessCheckpointSnapshot> => {
    const { data } = await api.get("/compliance/readiness-checkpoints");
    return data;
  },

  getTrustMetrics: async (): Promise<ComplianceTrustMetrics> => {
    const { data } = await api.get("/compliance/trust-metrics");
    return data;
  },

  getGovCloudProfile: async (): Promise<GovCloudDeploymentProfile> => {
    const { data } = await api.get("/compliance/govcloud-profile");
    return data;
  },

  getTrustCenter: async (): Promise<TrustCenterProfile> => {
    const { data } = await api.get("/compliance/trust-center");
    return data;
  },

  updateTrustCenterPolicy: async (
    payload: TrustCenterPolicyUpdate
  ): Promise<TrustCenterProfile> => {
    const { data } = await api.patch("/compliance/trust-center", payload);
    return data;
  },

  exportTrustCenterEvidenceWithOptions: async (params?: {
    format?: "json" | "csv" | "pdf";
    signed?: boolean;
  }): Promise<Blob> => {
    const { data } = await api.get("/compliance/trust-center/evidence-export", {
      params,
      responseType: "blob",
    });
    return data;
  },

  exportThreePAOPackage: async (params?: { signed?: boolean }): Promise<Blob> => {
    const { data } = await api.get("/compliance/three-pao-package", {
      params,
      responseType: "blob",
    });
    return data;
  },

  listCheckpointEvidence: async (
    checkpointId: string
  ): Promise<ComplianceCheckpointEvidenceItem[]> => {
    const { data } = await api.get(`/compliance/readiness-checkpoints/${checkpointId}/evidence`);
    return data;
  },

  createCheckpointEvidence: async (
    checkpointId: string,
    payload: ComplianceCheckpointEvidenceCreate
  ): Promise<ComplianceCheckpointEvidenceItem> => {
    const { data } = await api.post(
      `/compliance/readiness-checkpoints/${checkpointId}/evidence`,
      payload
    );
    return data;
  },

  updateCheckpointEvidence: async (
    checkpointId: string,
    linkId: number,
    payload: ComplianceCheckpointEvidenceUpdate
  ): Promise<ComplianceCheckpointEvidenceItem> => {
    const { data } = await api.patch(
      `/compliance/readiness-checkpoints/${checkpointId}/evidence/${linkId}`,
      payload
    );
    return data;
  },

  getCheckpointSignoff: async (checkpointId: string): Promise<ComplianceCheckpointSignoff> => {
    const { data } = await api.get(`/compliance/readiness-checkpoints/${checkpointId}/signoff`);
    return data;
  },

  listRegistryEvidence: async (params?: {
    scope?: "mine" | "organization";
    evidence_type?: string;
    skip?: number;
    limit?: number;
  }): Promise<ComplianceRegistryEvidenceItem[]> => {
    const { data } = await api.get("/compliance-registry/evidence", { params });
    return data;
  },

  upsertCheckpointSignoff: async (
    checkpointId: string,
    payload: ComplianceCheckpointSignoffWrite
  ): Promise<ComplianceCheckpointSignoff> => {
    const { data } = await api.put(
      `/compliance/readiness-checkpoints/${checkpointId}/signoff`,
      payload
    );
    return data;
  },
};

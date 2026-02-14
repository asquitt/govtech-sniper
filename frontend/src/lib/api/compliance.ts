import api from "./client";
import type {
  CMMCStatus,
  NISTOverview,
  DataPrivacyInfo,
  ComplianceAuditSummary,
  ComplianceReadiness,
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

  exportTrustCenterEvidence: async (): Promise<Blob> => {
    const { data } = await api.get("/compliance/trust-center/evidence-export", {
      responseType: "blob",
    });
    return data;
  },
};

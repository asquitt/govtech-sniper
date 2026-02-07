import api from "./client";
import type {
  CMMCStatus,
  NISTOverview,
  DataPrivacyInfo,
  ComplianceAuditSummary,
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
};

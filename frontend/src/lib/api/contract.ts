import api from "./client";
import type {
  ContractAward,
  ContractDeliverable,
  ContractStatus,
  DeliverableStatus,
  ContractTask,
  CPARSReview,
  CPARSEvidence,
  ContractStatusReport,
} from "@/types";

// =============================================================================
// Contract Endpoints
// =============================================================================

export const contractApi = {
  list: async (): Promise<{ contracts: ContractAward[]; total: number }> => {
    const { data } = await api.get("/contracts");
    return data;
  },

  create: async (payload: {
    contract_number: string;
    title: string;
    agency?: string | null;
    status?: ContractStatus;
    value?: number | null;
  }): Promise<ContractAward> => {
    const { data } = await api.post("/contracts", payload);
    return data;
  },

  update: async (
    contractId: number,
    payload: Partial<{
      title: string;
      agency: string | null;
      status: ContractStatus;
      value: number | null;
    }>
  ): Promise<ContractAward> => {
    const { data } = await api.patch(`/contracts/${contractId}`, payload);
    return data;
  },

  listDeliverables: async (contractId: number): Promise<ContractDeliverable[]> => {
    const { data } = await api.get(`/contracts/${contractId}/deliverables`);
    return data;
  },

  createDeliverable: async (
    contractId: number,
    payload: { title: string; status?: DeliverableStatus }
  ): Promise<ContractDeliverable> => {
    const { data } = await api.post(`/contracts/${contractId}/deliverables`, payload);
    return data;
  },

  listTasks: async (contractId: number): Promise<ContractTask[]> => {
    const { data } = await api.get(`/contracts/${contractId}/tasks`);
    return data;
  },

  createTask: async (
    contractId: number,
    payload: { title: string }
  ): Promise<ContractTask> => {
    const { data } = await api.post(`/contracts/${contractId}/tasks`, payload);
    return data;
  },

  listCPARS: async (contractId: number): Promise<CPARSReview[]> => {
    const { data } = await api.get(`/contracts/${contractId}/cpars`);
    return data;
  },

  createCPARS: async (
    contractId: number,
    payload: { overall_rating?: string; notes?: string }
  ): Promise<CPARSReview> => {
    const { data } = await api.post(`/contracts/${contractId}/cpars`, payload);
    return data;
  },

  listCPARSEvidence: async (
    contractId: number,
    cparsId: number
  ): Promise<CPARSEvidence[]> => {
    const { data } = await api.get(
      `/contracts/${contractId}/cpars/${cparsId}/evidence`
    );
    return data;
  },

  addCPARSEvidence: async (
    contractId: number,
    cparsId: number,
    payload: { document_id: number; citation?: string; notes?: string }
  ): Promise<CPARSEvidence> => {
    const { data } = await api.post(
      `/contracts/${contractId}/cpars/${cparsId}/evidence`,
      payload
    );
    return data;
  },

  deleteCPARSEvidence: async (
    contractId: number,
    cparsId: number,
    evidenceId: number
  ): Promise<void> => {
    await api.delete(
      `/contracts/${contractId}/cpars/${cparsId}/evidence/${evidenceId}`
    );
  },

  listStatusReports: async (
    contractId: number
  ): Promise<ContractStatusReport[]> => {
    const { data } = await api.get(`/contracts/${contractId}/status-reports`);
    return data;
  },

  createStatusReport: async (
    contractId: number,
    payload: {
      period_start?: string;
      period_end?: string;
      summary?: string;
      accomplishments?: string;
      risks?: string;
      next_steps?: string;
    }
  ): Promise<ContractStatusReport> => {
    const { data } = await api.post(
      `/contracts/${contractId}/status-reports`,
      payload
    );
    return data;
  },

  updateStatusReport: async (
    reportId: number,
    payload: Partial<ContractStatusReport>
  ): Promise<ContractStatusReport> => {
    const { data } = await api.patch(
      `/contracts/status-reports/${reportId}`,
      payload
    );
    return data;
  },

  deleteStatusReport: async (reportId: number): Promise<void> => {
    await api.delete(`/contracts/status-reports/${reportId}`);
  },
};

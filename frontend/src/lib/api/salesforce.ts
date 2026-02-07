import api from "./client";
import type {
  SalesforceStatus,
  SalesforceOpportunity,
  SalesforceSyncResult,
  SalesforceFieldMapping,
} from "@/types";

// =============================================================================
// Salesforce Endpoints
// =============================================================================

export const salesforceApi = {
  getStatus: async (): Promise<SalesforceStatus> => {
    const { data } = await api.get("/salesforce/status");
    return data;
  },

  listOpportunities: async (): Promise<SalesforceOpportunity[]> => {
    const { data } = await api.get("/salesforce/opportunities");
    return data;
  },

  sync: async (): Promise<SalesforceSyncResult> => {
    const { data } = await api.post("/salesforce/sync", {});
    return data;
  },

  listFieldMappings: async (): Promise<SalesforceFieldMapping[]> => {
    const { data } = await api.get("/salesforce/field-mappings");
    return data;
  },

  createFieldMapping: async (payload: {
    sniper_field: string;
    salesforce_field: string;
    direction?: string;
    transform?: string | null;
  }): Promise<SalesforceFieldMapping> => {
    const { data } = await api.post("/salesforce/field-mappings", payload);
    return data;
  },

  deleteFieldMapping: async (mappingId: number): Promise<void> => {
    await api.delete(`/salesforce/field-mappings/${mappingId}`);
  },
};

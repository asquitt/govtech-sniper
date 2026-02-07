import api from "./client";
import type { KnowledgeBaseDocument } from "@/types";

// =============================================================================
// Document Endpoints
// =============================================================================

export const documentApi = {
  list: async (params?: {
    document_type?: string;
    ready_only?: boolean;
  }): Promise<KnowledgeBaseDocument[]> => {
    const { data } = await api.get("/documents", { params });
    return data.documents ?? [];
  },

  get: async (documentId: number): Promise<KnowledgeBaseDocument> => {
    const { data } = await api.get(`/documents/${documentId}`);
    return data;
  },

  upload: async (
    file: File,
    metadata: {
      title: string;
      document_type: string;
      description?: string;
    }
  ): Promise<KnowledgeBaseDocument> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", metadata.title);
    formData.append("document_type", metadata.document_type);
    if (metadata.description) {
      formData.append("description", metadata.description);
    }

    const { data } = await api.post("/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  update: async (
    documentId: number,
    updates: Partial<KnowledgeBaseDocument>
  ): Promise<KnowledgeBaseDocument> => {
    const { data } = await api.patch(`/documents/${documentId}`, updates);
    return data;
  },

  delete: async (documentId: number): Promise<void> => {
    await api.delete(`/documents/${documentId}`);
  },

  getTypes: async (): Promise<{ value: string; label: string }[]> => {
    const { data } = await api.get("/documents/types/list");
    return data;
  },
};

// =============================================================================
// Export Endpoints
// =============================================================================

export const exportApi = {
  exportProposalDocx: async (proposalId: number): Promise<Blob> => {
    const { data } = await api.get(`/export/proposals/${proposalId}/docx`, {
      responseType: "blob",
    });
    return data;
  },

  exportProposalPdf: async (proposalId: number): Promise<Blob> => {
    const { data } = await api.get(`/export/proposals/${proposalId}/pdf`, {
      responseType: "blob",
    });
    return data;
  },

  exportComplianceMatrix: async (
    rfpId: number,
    format: "xlsx" | "csv" = "xlsx"
  ): Promise<Blob> => {
    const safeFormat = format === "csv" ? "xlsx" : format;
    const { data } = await api.get(
      `/export/rfps/${rfpId}/compliance-matrix/${safeFormat}`,
      {
      responseType: "blob",
      }
    );
    return data;
  },
};

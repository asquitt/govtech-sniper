import api from "./client";
import type {
  SharePointFile,
  SharePointUploadResult,
  SharePointStatus,
} from "@/types";

export const sharepointApi = {
  browse: async (path: string = "/"): Promise<SharePointFile[]> => {
    const { data } = await api.get("/sharepoint/browse", { params: { path } });
    return data;
  },

  download: async (fileId: string): Promise<Blob> => {
    const { data } = await api.get(`/sharepoint/download/${fileId}`, {
      responseType: "blob",
    });
    return data;
  },

  export: async (
    proposalId: number,
    folder: string = "/Proposals",
    format: "docx" | "pdf" = "docx"
  ): Promise<SharePointUploadResult> => {
    const { data } = await api.post("/sharepoint/export", null, {
      params: { proposal_id: proposalId, folder, format },
    });
    return data;
  },

  status: async (): Promise<SharePointStatus> => {
    const { data } = await api.get("/sharepoint/status");
    return data;
  },
};

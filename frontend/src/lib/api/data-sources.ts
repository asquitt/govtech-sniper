import api from "./client";
import type {
  DataSourceProvider,
  DataSourceSearchParams,
  DataSourceSearchResponse,
  DataSourceIngestResponse,
  DataSourceHealthResponse,
} from "@/types/data-sources";

// =============================================================================
// Data Sources API
// =============================================================================

export const dataSourcesApi = {
  listProviders: async (): Promise<DataSourceProvider[]> => {
    const { data } = await api.get("/data-sources");
    return data;
  },

  searchProvider: async (
    providerName: string,
    params: DataSourceSearchParams
  ): Promise<DataSourceSearchResponse> => {
    const { data } = await api.post(`/data-sources/${providerName}/search`, params);
    return data;
  },

  ingestFromProvider: async (
    providerName: string,
    params: DataSourceSearchParams
  ): Promise<DataSourceIngestResponse> => {
    const { data } = await api.post(`/data-sources/${providerName}/ingest`, params);
    return data;
  },

  checkHealth: async (providerName: string): Promise<DataSourceHealthResponse> => {
    const { data } = await api.get(`/data-sources/${providerName}/health`);
    return data;
  },
};

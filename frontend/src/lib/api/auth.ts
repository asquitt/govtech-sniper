import api from "./client";
import { tokenManager } from "./client";

// =============================================================================
// Auth Endpoints
// =============================================================================

export const authApi = {
  register: async (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }): Promise<{ access_token: string; refresh_token: string }> => {
    const response = await api.post("/auth/register", data);
    tokenManager.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  login: async (email: string, password: string): Promise<{ access_token: string; refresh_token: string }> => {
    const response = await api.post("/auth/login", { email, password });
    tokenManager.setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await api.post("/auth/logout");
    } finally {
      tokenManager.clearTokens();
    }
  },

  getMe: async (): Promise<{
    id: number;
    email: string;
    full_name: string | null;
    company_name: string | null;
    tier: string;
    api_calls_today: number;
    api_calls_limit: number;
  }> => {
    const { data } = await api.get("/auth/me");
    return data;
  },

  getProfile: async (): Promise<{
    naics_codes: string[];
    clearance_level: string;
    set_aside_types: string[];
    preferred_states: string[];
    min_contract_value: number | null;
    max_contract_value: number | null;
    include_keywords: string[];
    exclude_keywords: string[];
  }> => {
    const { data } = await api.get("/auth/profile");
    return data;
  },

  updateProfile: async (profile: {
    naics_codes?: string[];
    clearance_level?: string;
    set_aside_types?: string[];
    preferred_states?: string[];
    min_contract_value?: number;
    max_contract_value?: number;
    include_keywords?: string[];
    exclude_keywords?: string[];
  }): Promise<{ message: string }> => {
    const { data } = await api.put("/auth/profile", profile);
    return data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<{ message: string }> => {
    const { data } = await api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return data;
  },
};

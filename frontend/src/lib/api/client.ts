import axios from "axios";
import type { TaskStatus } from "@/types";

// =============================================================================
// API Client Configuration
// =============================================================================

// Direct backend URL (used for SSR, WebSocket, and token refresh)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

// Client-side requests go through the Next.js rewrite proxy (/api/* → backend)
// to avoid CORS issues. SSR requests use the direct backend URL.
const isServer = typeof window === "undefined";
const CLIENT_BASE_URL = isServer ? `${API_BASE_URL}/api/v1` : "/api";

const api = axios.create({
  baseURL: CLIENT_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token storage keys
const ACCESS_TOKEN_KEY = "rfp_sniper_access_token";
const REFRESH_TOKEN_KEY = "rfp_sniper_refresh_token";

// =============================================================================
// Auth Token Management
// =============================================================================

export const tokenManager = {
  getAccessToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  setTokens: (accessToken: string, refreshToken: string): void => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  },

  clearTokens: (): void => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },

  isAuthenticated: (): boolean => {
    return !!tokenManager.getAccessToken();
  },
};

// Add auth header interceptor
api.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retrying, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = tokenManager.getRefreshToken();
      if (refreshToken) {
        try {
          const refreshUrl = isServer
            ? `${API_BASE_URL}/api/v1/auth/refresh`
            : "/api/auth/refresh";
          const { data } = await axios.post(refreshUrl, {
            refresh_token: refreshToken,
          });

          tokenManager.setTokens(data.access_token, data.refresh_token);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          tokenManager.clearTokens();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
      }
    }

    return Promise.reject(error);
  }
);

// =============================================================================
// WebSocket Utilities
// =============================================================================

export const createWebSocket = (token: string): WebSocket => {
  const wsUrl = API_BASE_URL.replace(/^http/, "ws");
  return new WebSocket(`${wsUrl}/ws?token=${token}`);
};

export const useTaskWebSocket = (
  taskId: string,
  onUpdate: (status: TaskStatus) => void
): (() => void) => {
  const token = tokenManager.getAccessToken();
  if (!token) {
    console.error("No auth token available for WebSocket");
    return () => {};
  }

  const ws = createWebSocket(token);

  ws.onopen = () => {
    ws.send(JSON.stringify({ action: "watch", task_id: taskId }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "task_update" && data.task_id === taskId) {
        onUpdate(data.status);
      }
    } catch (e) {
      console.error("WebSocket message parse error:", e);
    }
  };

  ws.onerror = (error) => {
    console.error("WebSocket error:", error);
  };

  // Return cleanup function
  return () => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: "unwatch", task_id: taskId }));
    }
    ws.close();
  };
};

export { api };
export default api;

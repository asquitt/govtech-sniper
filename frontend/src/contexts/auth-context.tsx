"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authApi, tokenManager } from "@/lib/api";

interface User {
  id: number;
  email: string;
  full_name: string | null;
  company_name: string | null;
  tier: string;
  api_calls_today: number;
  api_calls_limit: number;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string, redirectTo?: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }, redirectTo?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      if (!tokenManager.isAuthenticated()) {
        setUser(null);
        return;
      }

      const userData = await authApi.getMe();
      setUser(userData);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      setUser(null);
      tokenManager.clearTokens();
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      await refreshUser();
      setIsLoading(false);
    };

    initAuth();
  }, [refreshUser]);

  const login = async (email: string, password: string, redirectTo?: string) => {
    await authApi.login(email, password);
    await refreshUser();
    const safeRedirect = redirectTo?.startsWith("/") ? redirectTo : "/opportunities";
    router.push(safeRedirect);
  };

  const register = async (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }, redirectTo?: string) => {
    await authApi.register(data);
    await refreshUser();
    const safeRedirect = redirectTo?.startsWith("/") ? redirectTo : "/opportunities";
    router.push(safeRedirect);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setUser(null);
      router.push("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useRequireAuth() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const nextPath =
        typeof window !== "undefined"
          ? `${window.location.pathname}${window.location.search}`
          : "/opportunities";
      router.push(`/login?next=${encodeURIComponent(nextPath)}`);
    }
  }, [isAuthenticated, isLoading, router]);

  return { isAuthenticated, isLoading };
}

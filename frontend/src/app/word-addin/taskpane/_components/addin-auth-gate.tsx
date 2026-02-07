"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api/auth";
import { tokenManager } from "@/lib/api/client";

interface AddinAuthGateProps {
  children: React.ReactNode;
}

export function AddinAuthGate({ children }: AddinAuthGateProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    tokenManager.isAuthenticated()
  );
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isAuthenticated) {
    return <>{children}</>;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await authApi.login(email, password);
      setIsAuthenticated(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Login failed. Check credentials."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Sign in to access your proposals.
      </p>
      <form onSubmit={handleLogin} className="space-y-2">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm"
          required
        />
        {error && <p className="text-xs text-red-500">{error}</p>}
        <Button type="submit" className="w-full" size="sm" disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            "Sign In"
          )}
        </Button>
      </form>
    </div>
  );
}

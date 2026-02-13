"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center max-w-md">
        <h2 className="text-lg font-semibold text-destructive mb-2">
          Something went wrong
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          {error.message || "An unexpected error occurred."}
        </p>
        <button
          onClick={reset}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

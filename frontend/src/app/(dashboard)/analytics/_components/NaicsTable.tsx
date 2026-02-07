"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NAICSPerformanceData } from "@/types";

interface NaicsTableProps {
  data: NAICSPerformanceData | null;
  loading: boolean;
}

export function NaicsTable({ data, loading }: NaicsTableProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">NAICS Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const entries = data?.entries ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">NAICS Performance</CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No NAICS performance data yet
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pb-2 font-medium text-muted-foreground">NAICS</th>
                  <th className="pb-2 font-medium text-muted-foreground text-right">Total</th>
                  <th className="pb-2 font-medium text-muted-foreground text-right">Won</th>
                  <th className="pb-2 font-medium text-muted-foreground text-right">Lost</th>
                  <th className="pb-2 font-medium text-muted-foreground text-right">Win Rate</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.naics_code} className="border-b border-border/50">
                    <td className="py-2 font-mono">{entry.naics_code}</td>
                    <td className="py-2 text-right">{entry.total}</td>
                    <td className="py-2 text-right text-green-500">{entry.won}</td>
                    <td className="py-2 text-right text-red-500">{entry.lost}</td>
                    <td className="py-2 text-right font-medium">{entry.win_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

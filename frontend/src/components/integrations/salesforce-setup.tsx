"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Trash2,
  Plus,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { salesforceApi } from "@/lib/api";
import type {
  SalesforceStatus,
  SalesforceOpportunity,
  SalesforceFieldMapping,
  SalesforceSyncResult,
} from "@/types";

const SNIPER_FIELDS = [
  "stage", "bid_decision", "win_probability", "notes", "rfp_title", "response_date",
];
const SF_FIELDS = [
  "StageName", "Amount", "Probability", "Description", "Name", "CloseDate",
];
const DIRECTIONS: { value: "push" | "pull" | "both"; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "push", label: "Push" },
  { value: "pull", label: "Pull" },
];

function DirIcon({ d }: { d: string }) {
  if (d === "push") return <ArrowUp className="h-4 w-4" />;
  if (d === "pull") return <ArrowDown className="h-4 w-4" />;
  return <ArrowUpDown className="h-4 w-4" />;
}

function StatusBadge({ status }: { status: SalesforceStatus | null }) {
  if (!status) return <Badge variant="secondary">Loading...</Badge>;
  if (!status.configured) return <Badge variant="secondary">Not Configured</Badge>;
  if (!status.enabled) return <Badge variant="outline">Disabled</Badge>;
  if (status.connected)
    return (
      <Badge className="bg-green-100 text-green-800">
        <CheckCircle2 className="mr-1 h-3 w-3" /> Connected
      </Badge>
    );
  return (
    <Badge variant="destructive">
      <AlertCircle className="mr-1 h-3 w-3" /> Disconnected
    </Badge>
  );
}

function MappingsTable({
  mappings,
  onDelete,
  onAdd,
}: {
  mappings: SalesforceFieldMapping[];
  onDelete: (id: number) => void;
  onAdd: (sniper: string, sf: string, dir: "push" | "pull" | "both") => void;
}) {
  const [sniper, setSniper] = useState(SNIPER_FIELDS[0]);
  const [sf, setSf] = useState(SF_FIELDS[0]);
  const [dir, setDir] = useState<"push" | "pull" | "both">("both");

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <h3 className="font-medium">Field Mappings</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2 pr-4">Sniper Field</th>
            <th className="pb-2 pr-4">Direction</th>
            <th className="pb-2 pr-4">Salesforce Field</th>
            <th className="pb-2 w-10" />
          </tr>
        </thead>
        <tbody>
          {mappings.map((m) => (
            <tr key={m.id} className="border-b last:border-0">
              <td className="py-2 pr-4 font-mono text-xs">{m.sniper_field}</td>
              <td className="py-2 pr-4">
                <span className="inline-flex items-center gap-1 text-gray-600">
                  <DirIcon d={m.direction} /> {m.direction}
                </span>
              </td>
              <td className="py-2 pr-4 font-mono text-xs">{m.salesforce_field}</td>
              <td className="py-2">
                <button onClick={() => onDelete(m.id)} className="text-red-500 hover:text-red-700">
                  <Trash2 className="h-4 w-4" />
                </button>
              </td>
            </tr>
          ))}
          {mappings.length === 0 && (
            <tr><td colSpan={4} className="py-4 text-center text-gray-400">No field mappings.</td></tr>
          )}
        </tbody>
      </table>
      <div className="flex items-center gap-2 pt-2">
        <select value={sniper} onChange={(e) => setSniper(e.target.value)} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm">
          {SNIPER_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <select value={dir} onChange={(e) => setDir(e.target.value as "push" | "pull" | "both")} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm">
          {DIRECTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select value={sf} onChange={(e) => setSf(e.target.value)} className="rounded-md border border-gray-300 px-2 py-1.5 text-sm">
          {SF_FIELDS.map((f) => <option key={f} value={f}>{f}</option>)}
        </select>
        <Button size="sm" variant="outline" onClick={() => onAdd(sniper, sf, dir)}>
          <Plus className="mr-1 h-4 w-4" /> Add
        </Button>
      </div>
    </div>
  );
}

function OpportunitiesTable({ items }: { items: SalesforceOpportunity[] }) {
  if (items.length === 0) return <p className="text-sm text-gray-400 p-4">No opportunities found.</p>;
  return (
    <div className="border rounded-lg p-4 space-y-3">
      <h3 className="font-medium">Salesforce Opportunities ({items.length})</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2 pr-4">Name</th>
            <th className="pb-2 pr-4">Stage</th>
            <th className="pb-2 pr-4">Amount</th>
            <th className="pb-2 pr-4">Close Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map((o) => (
            <tr key={o.sf_id} className="border-b last:border-0">
              <td className="py-2 pr-4 font-medium">{o.name}</td>
              <td className="py-2 pr-4"><Badge variant="secondary">{o.stage ?? "—"}</Badge></td>
              <td className="py-2 pr-4">{o.amount != null ? `$${o.amount.toLocaleString()}` : "—"}</td>
              <td className="py-2 pr-4">{o.close_date ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SalesforceSetup() {
  const [status, setStatus] = useState<SalesforceStatus | null>(null);
  const [mappings, setMappings] = useState<SalesforceFieldMapping[]>([]);
  const [opps, setOpps] = useState<SalesforceOpportunity[]>([]);
  const [syncResult, setSyncResult] = useState<SalesforceSyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try { const s = await salesforceApi.getStatus(); setStatus(s); return s; }
    catch { setStatus({ configured: false, enabled: false, connected: false }); return null; }
  }, []);

  const loadMappings = useCallback(async () => {
    try { setMappings(await salesforceApi.listFieldMappings()); } catch { /* not configured */ }
  }, []);

  const loadOpps = useCallback(async () => {
    try { setOpps(await salesforceApi.listOpportunities()); } catch { /* not connected */ }
  }, []);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const s = await loadStatus();
      if (s?.connected) await Promise.all([loadMappings(), loadOpps()]);
      setLoading(false);
    })();
  }, [loadStatus, loadMappings, loadOpps]);

  const handleSync = async () => {
    setSyncing(true); setError(null); setSyncResult(null);
    try {
      const r = await salesforceApi.sync(); setSyncResult(r);
      if (r.status === "success") await loadOpps();
    } catch (e) { setError(e instanceof Error ? e.message : "Sync failed"); }
    finally { setSyncing(false); }
  };

  const handleAddMapping = async (sniper: string, sf: string, dir: "push" | "pull" | "both") => {
    try {
      const created = await salesforceApi.createFieldMapping({ sniper_field: sniper, salesforce_field: sf, direction: dir });
      setMappings((p) => [...p, created]);
    } catch (e) { setError(e instanceof Error ? e.message : "Failed to add mapping"); }
  };

  const handleDeleteMapping = async (id: number) => {
    try { await salesforceApi.deleteFieldMapping(id); setMappings((p) => p.filter((m) => m.id !== id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed to delete mapping"); }
  };

  if (loading) return (
    <div className="space-y-4 p-6">
      <div className="animate-pulse h-6 w-48 bg-gray-200 rounded" />
      <div className="animate-pulse h-32 bg-gray-200 rounded" />
    </div>
  );

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Salesforce Integration</h2>
          <p className="text-sm text-gray-500 mt-1">Sync capture plans with Salesforce CRM opportunities.</p>
        </div>
        <StatusBadge status={status} />
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 flex-shrink-0" /> {error}
        </div>
      )}

      {status && !status.configured && (
        <div className="rounded-md bg-yellow-50 p-4 text-sm text-yellow-800">
          Salesforce is not configured. Go to <span className="font-medium">Settings &gt; Integrations</span> and add your credentials.
        </div>
      )}

      {status?.connected && (
        <>
          <div className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">Bidirectional Sync</h3>
              <Button onClick={handleSync} disabled={syncing} size="sm">
                <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing..." : "Sync Now"}
              </Button>
            </div>
            {syncResult && (
              <div className={`text-sm rounded-md p-3 ${syncResult.status === "success" ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
                <p>Pushed: {syncResult.pushed} | Pulled: {syncResult.pulled}</p>
                {syncResult.errors.length > 0 && (
                  <ul className="mt-1 list-disc pl-4">{syncResult.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
                )}
              </div>
            )}
          </div>
          <MappingsTable mappings={mappings} onDelete={handleDeleteMapping} onAdd={handleAddMapping} />
          <OpportunitiesTable items={opps} />
        </>
      )}
    </div>
  );
}

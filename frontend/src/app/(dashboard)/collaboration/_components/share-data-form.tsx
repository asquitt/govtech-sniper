"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { collaborationApi } from "@/lib/api";
import type {
  ContractFeedCatalogItem,
  ContractFeedPresetItem,
  SharedDataPermission,
  WorkspaceMember,
} from "@/types";

interface ShareDataFormProps {
  workspaceId: number;
  members: WorkspaceMember[];
  shareDataType: SharedDataPermission["data_type"];
  shareEntityId: string;
  contractFeedCatalog: ContractFeedCatalogItem[];
  contractFeedPresets: ContractFeedPresetItem[];
  selectedContractFeedId: string;
  selectedPresetKey: string;
  selectedPartnerUserId: string;
  expirationDays: string;
  requiresApproval: boolean;
  isSharing: boolean;
  isApplyingPreset: boolean;
  onShareDataTypeChange: (type: SharedDataPermission["data_type"]) => void;
  onShareEntityIdChange: (id: string) => void;
  onSelectedContractFeedIdChange: (id: string) => void;
  onSelectedPresetKeyChange: (key: string) => void;
  onSelectedPartnerUserIdChange: (id: string) => void;
  onExpirationDaysChange: (days: string) => void;
  onRequiresApprovalChange: (required: boolean) => void;
  onSharingChange: (sharing: boolean) => void;
  onApplyingPresetChange: (applying: boolean) => void;
  onDataChanged: () => Promise<void>;
}

export function ShareDataForm({
  workspaceId,
  members,
  shareDataType,
  shareEntityId,
  contractFeedCatalog,
  contractFeedPresets,
  selectedContractFeedId,
  selectedPresetKey,
  selectedPartnerUserId,
  expirationDays,
  requiresApproval,
  isSharing,
  isApplyingPreset,
  onShareDataTypeChange,
  onShareEntityIdChange,
  onSelectedContractFeedIdChange,
  onSelectedPresetKeyChange,
  onSelectedPartnerUserIdChange,
  onExpirationDaysChange,
  onRequiresApprovalChange,
  onSharingChange,
  onApplyingPresetChange,
  onDataChanged,
}: ShareDataFormProps) {
  const scopedMemberOptions = Array.from(
    new Map(members.map((member) => [member.user_id, member])).values()
  );

  return (
    <>
      {/* Apply Contract Feed Preset */}
      <div className="rounded-lg border border-border bg-card p-3">
        <p className="text-sm font-medium text-foreground mb-2">
          Apply Contract Feed Preset
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Preset</label>
            <select
              className="h-9 min-w-64 rounded-md border border-input bg-background px-3 text-sm"
              aria-label="Contract feed preset"
              value={selectedPresetKey}
              onChange={(e) => onSelectedPresetKeyChange(e.target.value)}
            >
              {contractFeedPresets.length === 0 && (
                <option value="">No presets available</option>
              )}
              {contractFeedPresets.map((preset) => (
                <option key={preset.key} value={preset.key}>
                  {preset.name}
                </option>
              ))}
            </select>
            {selectedPresetKey && (
              <p className="mt-1 text-[11px] text-muted-foreground">
                {
                  contractFeedPresets.find((preset) => preset.key === selectedPresetKey)
                    ?.description
                }
              </p>
            )}
          </div>
          <Button
            size="sm"
            disabled={isApplyingPreset || !selectedPresetKey}
            onClick={async () => {
              if (!selectedPresetKey) return;
              onApplyingPresetChange(true);
              try {
                await collaborationApi.applyContractFeedPreset(
                  workspaceId,
                  selectedPresetKey
                );
                await onDataChanged();
              } catch {
                /* handled by interceptor */
              } finally {
                onApplyingPresetChange(false);
              }
            }}
          >
            Apply Preset
          </Button>
        </div>
      </div>

      {/* Share New Data */}
      <div className="rounded-lg border border-border bg-card p-3">
        <p className="text-sm font-medium text-foreground mb-2">Share New Data</p>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Type</label>
            <select
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              aria-label="Shared data type"
              value={shareDataType}
              onChange={(e) =>
                onShareDataTypeChange(e.target.value as SharedDataPermission["data_type"])
              }
            >
              <option value="rfp_summary">RFP Summary</option>
              <option value="compliance_matrix">Compliance Matrix</option>
              <option value="proposal_section">Proposal Section</option>
              <option value="forecast">Forecast</option>
              <option value="contract_feed">Contract Feed</option>
            </select>
          </div>
          {shareDataType === "contract_feed" ? (
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                Contract Feed
              </label>
              <select
                className="h-9 min-w-56 rounded-md border border-input bg-background px-3 text-sm"
                aria-label="Contract Feed"
                value={selectedContractFeedId}
                onChange={(e) => onSelectedContractFeedIdChange(e.target.value)}
              >
                {contractFeedCatalog.length === 0 && (
                  <option value="">No feeds available</option>
                )}
                {contractFeedCatalog.map((feed) => (
                  <option key={feed.id} value={feed.id}>
                    {feed.name}
                  </option>
                ))}
              </select>
              {selectedContractFeedId && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {
                    contractFeedCatalog.find(
                      (feed) => String(feed.id) === selectedContractFeedId
                    )?.description
                  }
                </p>
              )}
            </div>
          ) : (
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">Entity ID</label>
              <input
                type="number"
                min={1}
                aria-label="Shared entity id"
                className="h-9 w-32 rounded-md border border-input bg-background px-3 text-sm"
                value={shareEntityId}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => onShareEntityIdChange(e.target.value)}
                placeholder="123"
              />
            </div>
          )}
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Visible To</label>
            <select
              className="h-9 min-w-48 rounded-md border border-input bg-background px-3 text-sm"
              aria-label="Visible To"
              value={selectedPartnerUserId}
              onChange={(event) => onSelectedPartnerUserIdChange(event.target.value)}
            >
              <option value="">All members</option>
              {scopedMemberOptions.map((member) => (
                <option key={member.id} value={member.user_id}>
                  {member.user_name || member.user_email || `User #${member.user_id}`}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Expiry</label>
            <select
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              aria-label="Share Expiry"
              value={expirationDays}
              onChange={(event) => onExpirationDaysChange(event.target.value)}
            >
              <option value="">No expiry</option>
              <option value="7">7 days</option>
              <option value="14">14 days</option>
              <option value="30">30 days</option>
            </select>
          </div>
          <label className="mb-1 flex h-9 items-center gap-2 rounded-md border border-input px-3 text-xs text-foreground">
            <input
              type="checkbox"
              aria-label="Require approval"
              checked={requiresApproval}
              onChange={(event) => onRequiresApprovalChange(event.target.checked)}
            />
            Require approval
          </label>
          <Button
            size="sm"
            disabled={
              isSharing ||
              (shareDataType === "contract_feed"
                ? !selectedContractFeedId
                : !shareEntityId.trim())
            }
            onClick={async () => {
              const entityId = Number.parseInt(
                shareDataType === "contract_feed"
                  ? selectedContractFeedId
                  : shareEntityId,
                10
              );
              if (!Number.isFinite(entityId) || entityId <= 0) return;
              const expiresAt = expirationDays
                ? new Date(Date.now() + Number.parseInt(expirationDays, 10) * 86_400_000)
                : null;
              onSharingChange(true);
              try {
                await collaborationApi.shareData(workspaceId, {
                  data_type: shareDataType,
                  entity_id: entityId,
                  requires_approval: requiresApproval,
                  partner_user_id: selectedPartnerUserId
                    ? Number.parseInt(selectedPartnerUserId, 10)
                    : null,
                  expires_at: expiresAt?.toISOString() ?? null,
                });
                onShareEntityIdChange("");
                onExpirationDaysChange("");
                onSelectedPartnerUserIdChange("");
                onRequiresApprovalChange(false);
                await onDataChanged();
              } catch {
                /* handled by interceptor */
              } finally {
                onSharingChange(false);
              }
            }}
          >
            Share
          </Button>
        </div>
      </div>
    </>
  );
}

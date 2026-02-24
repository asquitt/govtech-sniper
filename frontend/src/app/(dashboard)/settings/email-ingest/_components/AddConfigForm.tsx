"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { SharedWorkspace } from "@/types";

const INPUT_CLASS =
  "rounded-md border border-border bg-background px-3 py-2 text-sm w-full";

interface AddConfigFormProps {
  imapServer: string;
  imapPort: string;
  email: string;
  password: string;
  folder: string;
  workspaceId: string;
  autoCreateRfps: boolean;
  minConfidence: string;
  workspaces: SharedWorkspace[];
  loading: boolean;
  onImapServerChange: (value: string) => void;
  onImapPortChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onFolderChange: (value: string) => void;
  onWorkspaceIdChange: (value: string) => void;
  onAutoCreateRfpsChange: (value: boolean) => void;
  onMinConfidenceChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function AddConfigForm({
  imapServer,
  imapPort,
  email,
  password,
  folder,
  workspaceId,
  autoCreateRfps,
  minConfidence,
  workspaces,
  loading,
  onImapServerChange,
  onImapPortChange,
  onEmailChange,
  onPasswordChange,
  onFolderChange,
  onWorkspaceIdChange,
  onAutoCreateRfpsChange,
  onMinConfidenceChange,
  onSubmit,
}: AddConfigFormProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4">
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="imap-server">
                IMAP Server
              </label>
              <input
                id="imap-server"
                className={INPUT_CLASS}
                placeholder="imap.gmail.com"
                value={imapServer}
                onChange={(e) => onImapServerChange(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="imap-port">
                IMAP Port
              </label>
              <input
                id="imap-port"
                className={INPUT_CLASS}
                placeholder="993"
                type="number"
                value={imapPort}
                onChange={(e) => onImapPortChange(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="email-address">
                Email Address
              </label>
              <input
                id="email-address"
                className={INPUT_CLASS}
                placeholder="capture@example.com"
                type="email"
                value={email}
                onChange={(e) => onEmailChange(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="email-password">
                App Password
              </label>
              <input
                id="email-password"
                className={INPUT_CLASS}
                placeholder="Password / App password"
                type="password"
                value={password}
                onChange={(e) => onPasswordChange(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="email-folder">
                Folder
              </label>
              <input
                id="email-folder"
                className={INPUT_CLASS}
                placeholder="INBOX"
                value={folder}
                onChange={(e) => onFolderChange(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground" htmlFor="workspace-routing">
                Team Workspace (Optional)
              </label>
              <select
                id="workspace-routing"
                className={INPUT_CLASS}
                value={workspaceId}
                onChange={(e) => onWorkspaceIdChange(e.target.value)}
              >
                <option value="">No routing workspace</option>
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={autoCreateRfps}
                onChange={(e) => onAutoCreateRfpsChange(e.target.checked)}
              />
              Auto-create opportunities for qualified emails
            </label>
            <div className="space-y-1">
              <label
                className="text-xs text-muted-foreground"
                htmlFor="confidence-threshold"
              >
                Minimum RFP Confidence (0-1)
              </label>
              <input
                id="confidence-threshold"
                className={INPUT_CLASS}
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={minConfidence}
                onChange={(e) => onMinConfidenceChange(e.target.value)}
              />
            </div>
          </div>
          <Button type="submit" disabled={loading}>
            {loading ? "Saving..." : "Save Configuration"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

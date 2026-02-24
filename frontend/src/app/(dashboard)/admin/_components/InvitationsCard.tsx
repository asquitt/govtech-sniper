"use client";

import type { OrgMemberInvitation, OrgRole } from "@/types";

interface InvitationsCardProps {
  invitations: OrgMemberInvitation[];
  inviteEmail: string;
  inviteRole: OrgRole;
  inviteDays: number;
  inviteSubmitting: boolean;
  inviteError: string | null;
  onEmailChange: (email: string) => void;
  onRoleChange: (role: OrgRole) => void;
  onDaysChange: (days: number) => void;
  onSubmit: (event: React.FormEvent) => void;
  onActivate: (invitationId: number) => void;
  onRevoke: (invitationId: number) => void;
  onResend: (invitationId: number) => void;
  invitationSlaClass: (slaState: OrgMemberInvitation["sla_state"]) => string;
}

export function InvitationsCard({
  invitations,
  inviteEmail,
  inviteRole,
  inviteDays,
  inviteSubmitting,
  inviteError,
  onEmailChange,
  onRoleChange,
  onDaysChange,
  onSubmit,
  onActivate,
  onRevoke,
  onResend,
  invitationSlaClass,
}: InvitationsCardProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-4">
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Member Invitations</p>
        <p className="text-xs text-muted-foreground">
          Invite users by email, then activate once they register.
        </p>
      </div>
      <form className="grid gap-2 md:grid-cols-4" onSubmit={onSubmit}>
        <input
          aria-label="Invite member email"
          className="md:col-span-2 rounded-md border border-border bg-background px-3 py-2 text-sm"
          placeholder="new-member@example.com"
          value={inviteEmail}
          onChange={(event) => onEmailChange(event.target.value)}
        />
        <select
          aria-label="Invite role"
          className="rounded-md border border-border bg-background px-3 py-2 text-sm"
          value={inviteRole}
          onChange={(event) => onRoleChange(event.target.value as OrgRole)}
        >
          <option value="viewer">viewer</option>
          <option value="member">member</option>
          <option value="admin">admin</option>
          <option value="owner">owner</option>
        </select>
        <div className="flex items-center gap-2">
          <input
            aria-label="Invitation expiration days"
            type="number"
            min={1}
            max={30}
            className="w-20 rounded-md border border-border bg-background px-2 py-2 text-sm"
            value={inviteDays}
            onChange={(event) =>
              onDaysChange(Number.parseInt(event.target.value, 10) || 7)
            }
          />
          <button
            type="submit"
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground"
            disabled={inviteSubmitting}
          >
            {inviteSubmitting ? "Inviting..." : "Invite"}
          </button>
        </div>
      </form>
      {inviteError ? <p className="text-xs text-destructive">{inviteError}</p> : null}
      <div className="space-y-2">
        {invitations.length === 0 ? (
          <p className="text-xs text-muted-foreground">No invitations yet.</p>
        ) : (
          invitations.map((invitation) => (
            <div
              key={invitation.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border px-3 py-2"
              data-testid={`org-invitation-${invitation.id}`}
            >
              <div className="min-w-0">
                <p className="truncate text-sm text-foreground">{invitation.email}</p>
                <p className="text-xs text-muted-foreground">
                  {invitation.role} · {invitation.status} · expires{" "}
                  {new Date(invitation.expires_at).toLocaleDateString()}
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${invitationSlaClass(
                      invitation.sla_state
                    )}`}
                  >
                    SLA {invitation.sla_state}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Age {invitation.invite_age_days}d
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    Expires in {invitation.days_until_expiry}d
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-muted-foreground">
                  {invitation.activation_ready
                    ? "Registered"
                    : "Awaiting registration"}
                </span>
                <button
                  type="button"
                  className="inline-flex h-8 items-center rounded-md border border-border px-2 text-xs"
                  disabled={invitation.status === "activated"}
                  onClick={() => onResend(invitation.id)}
                >
                  Resend
                </button>
                <button
                  type="button"
                  className="inline-flex h-8 items-center rounded-md border border-border px-2 text-xs"
                  disabled={
                    invitation.status === "activated" ||
                    invitation.status === "revoked"
                  }
                  onClick={() => onRevoke(invitation.id)}
                >
                  Revoke
                </button>
                <button
                  type="button"
                  className="inline-flex h-8 items-center rounded-md border border-border px-2 text-xs"
                  disabled={
                    invitation.status !== "pending" || !invitation.activation_ready
                  }
                  onClick={() => onActivate(invitation.id)}
                >
                  Activate
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

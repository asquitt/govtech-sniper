"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Team, TeamMember, TeamRole } from "@/lib/api";

interface TeamRolesCardProps {
  teams: Team[];
  selectedTeamId: number | null;
  teamMembers: TeamMember[];
  roleEdits: Record<number, TeamRole>;
  isLoadingTeams: boolean;
  roleOptions: TeamRole[];
  onTeamChange: (teamId: number | null) => void;
  onRoleEdit: (userId: number, role: TeamRole) => void;
  onUpdateRole: (userId: number) => void;
}

export function TeamRolesCard({
  teams,
  selectedTeamId,
  teamMembers,
  roleEdits,
  isLoadingTeams,
  roleOptions,
  onTeamChange,
  onRoleEdit,
  onUpdateRole,
}: TeamRolesCardProps) {
  return (
    <Card className="border border-border">
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Team Roles</p>
            <p className="text-xs text-muted-foreground">
              Manage access levels for your team
            </p>
          </div>
          {isLoadingTeams && (
            <span className="text-xs text-muted-foreground">Loading...</span>
          )}
        </div>

        {teams.length === 0 ? (
          <p className="text-sm text-muted-foreground">No teams found.</p>
        ) : (
          <div className="space-y-3">
            <select
              className="w-full rounded-md border border-border bg-background px-2 py-1 text-sm"
              value={selectedTeamId ?? ""}
              onChange={(e) =>
                onTeamChange(e.target.value ? Number(e.target.value) : null)
              }
            >
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>

            <div className="space-y-2">
              {teamMembers.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No members found.
                </p>
              ) : (
                teamMembers.map((member) => (
                  <div
                    key={member.user_id}
                    className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
                  >
                    <div>
                      <p className="font-medium text-foreground">
                        {member.full_name || member.email}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {member.email}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                        value={roleEdits[member.user_id] || member.role}
                        onChange={(e) =>
                          onRoleEdit(member.user_id, e.target.value as TeamRole)
                        }
                      >
                        {roleOptions.map((role) => (
                          <option key={role} value={role}>
                            {role}
                          </option>
                        ))}
                      </select>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onUpdateRole(member.user_id)}
                      >
                        Update
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

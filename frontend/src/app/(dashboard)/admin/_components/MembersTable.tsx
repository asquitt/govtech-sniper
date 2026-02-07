"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Shield, User, UserX, UserCheck } from "lucide-react";
import type { OrgMember, OrgRole } from "@/types";

interface MembersTableProps {
  members: OrgMember[];
  loading: boolean;
  onRoleChange: (userId: number, role: OrgRole) => void;
  onDeactivate: (userId: number) => void;
  onReactivate: (userId: number) => void;
  currentUserId: number;
}

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-500/20 text-amber-400",
  admin: "bg-blue-500/20 text-blue-400",
  member: "bg-green-500/20 text-green-400",
  viewer: "bg-gray-500/20 text-gray-400",
};

export function MembersTable({
  members,
  loading,
  onRoleChange,
  onDeactivate,
  onReactivate,
  currentUserId,
}: MembersTableProps) {
  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5">
          <div className="animate-pulse space-y-3">
            <div className="h-5 w-40 bg-muted rounded" />
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 bg-muted rounded" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border border-border">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-medium text-foreground">
            Team Members ({members.length})
          </p>
        </div>

        <div className="space-y-2">
          {members.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border/50"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {member.full_name || member.email}
                    {member.user_id === currentUserId && (
                      <span className="text-xs text-muted-foreground ml-2">(You)</span>
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">{member.email}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {member.sso_provider && (
                  <Badge variant="outline" className="text-[10px]">
                    <Shield className="w-3 h-3 mr-1" />
                    {member.sso_provider}
                  </Badge>
                )}
                <Badge className={`text-[10px] ${ROLE_COLORS[member.role] || ""}`}>
                  {member.role}
                </Badge>
                {!member.is_active && (
                  <Badge variant="destructive" className="text-[10px]">
                    Deactivated
                  </Badge>
                )}

                {member.user_id !== currentUserId && (
                  <div className="flex gap-1 ml-2">
                    <select
                      className="text-xs bg-background border border-border rounded px-2 py-1"
                      value={member.role}
                      onChange={(e) => onRoleChange(member.user_id, e.target.value as OrgRole)}
                    >
                      <option value="owner">Owner</option>
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>

                    {member.is_active ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        title="Deactivate"
                        onClick={() => onDeactivate(member.user_id)}
                      >
                        <UserX className="w-3.5 h-3.5 text-destructive" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        title="Reactivate"
                        onClick={() => onReactivate(member.user_id)}
                      >
                        <UserCheck className="w-3.5 h-3.5 text-accent" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {members.length === 0 && (
            <div className="text-center py-6 text-muted-foreground">
              <p className="text-sm">No members found</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

import Link from "next/link";
import {
  ExternalLink,
  MoreHorizontal,
  Building2,
  Loader2,
  Target,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { formatDate } from "@/lib/utils";
import type { RFPListItem } from "@/types";
import {
  statusConfig,
  QualificationBadge,
  MatchScoreBadge,
  DeadlineBadge,
  formatSeconds,
} from "./opportunity-badges";

interface OpportunitiesTableProps {
  rfps: RFPListItem[];
  isLoading: boolean;
  searchQuery: string;
  isSyncing: boolean;
  syncCooldownSeconds: number;
  onSync: () => void;
}

export function OpportunitiesTable({
  rfps,
  isLoading,
  searchQuery,
  isSyncing,
  syncCooldownSeconds,
  onSync,
}: OpportunitiesTableProps) {
  return (
    <Card className="flex-1 overflow-hidden">
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : rfps.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64">
          <Target className="w-12 h-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground mb-4">
            {searchQuery
              ? "No opportunities match your search"
              : "No opportunities found"}
          </p>
          {!searchQuery && (
            <Button
              onClick={onSync}
              disabled={isSyncing || syncCooldownSeconds > 0}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              {syncCooldownSeconds > 0
                ? `Sync in ${formatSeconds(syncCooldownSeconds)}`
                : "Sync from SAM.gov"}
            </Button>
          )}
        </div>
      ) : (
        <ScrollArea className="h-[calc(100vh-380px)]">
          <table className="w-full">
            <thead className="sticky top-0 bg-card border-b border-border">
              <tr className="text-left text-sm text-muted-foreground">
                <th className="p-4 font-medium">Opportunity</th>
                <th className="p-4 font-medium">Agency</th>
                <th className="p-4 font-medium">Status</th>
                <th className="p-4 font-medium">Qualification</th>
                <th className="p-4 font-medium">Match</th>
                <th className="p-4 font-medium">Deadline</th>
                <th className="p-4 font-medium w-10"></th>
              </tr>
            </thead>
            <tbody>
              {rfps.map((rfp) => (
                <tr
                  key={rfp.id}
                  className="border-b border-border hover:bg-secondary/50 transition-colors"
                >
                  <td className="p-4">
                    <div className="flex flex-col gap-1">
                      <Link
                        href={`/opportunities/${rfp.id}`}
                        className="font-medium text-foreground hover:text-primary transition-colors line-clamp-1"
                      >
                        {rfp.title}
                      </Link>
                      <span className="text-xs text-muted-foreground font-mono">
                        {rfp.solicitation_number || rfp.notice_id}
                      </span>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{rfp.agency}</span>
                    </div>
                  </td>
                  <td className="p-4">
                    <Badge variant={statusConfig[rfp.status]?.variant || "default"}>
                      {rfp.status === "analyzing" && (
                        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                      )}
                      {statusConfig[rfp.status]?.label || rfp.status}
                    </Badge>
                  </td>
                  <td className="p-4">
                    <div className="flex flex-col gap-1">
                      <QualificationBadge
                        isQualified={rfp.is_qualified}
                        score={rfp.qualification_score}
                      />
                      {rfp.recommendation_score !== undefined && (
                        <Badge variant="outline" className="w-fit">
                          Rec {Math.round(rfp.recommendation_score)}%
                        </Badge>
                      )}
                    </div>
                  </td>
                  <td className="p-4">
                    <MatchScoreBadge score={rfp.match_score} />
                  </td>
                  <td className="p-4">
                    <div className="flex flex-col gap-0.5">
                      <DeadlineBadge deadline={rfp.response_deadline} />
                      <span className="text-xs text-muted-foreground">
                        {formatDate(rfp.response_deadline)}
                      </span>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/analysis/${rfp.id}`}>
                          <ExternalLink className="w-4 h-4" />
                        </Link>
                      </Button>
                      <Button variant="ghost" size="icon">
                        <MoreHorizontal className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      )}
    </Card>
  );
}

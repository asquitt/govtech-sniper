import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  daysUntilDeadline,
  getDeadlineUrgency,
  cn,
} from "@/lib/utils";
import { getApiErrorDetail } from "@/lib/api/error";
import type { RFPStatus } from "@/types";

export const statusConfig: Record<
  RFPStatus,
  { label: string; variant: "default" | "success" | "warning" | "destructive" }
> = {
  new: { label: "New", variant: "default" },
  analyzing: { label: "Analyzing", variant: "warning" },
  analyzed: { label: "Analyzed", variant: "success" },
  drafting: { label: "Drafting", variant: "warning" },
  ready: { label: "Ready", variant: "success" },
  submitted: { label: "Submitted", variant: "success" },
  archived: { label: "Archived", variant: "destructive" },
};

export function QualificationBadge({
  isQualified,
  score,
}: {
  isQualified?: boolean;
  score?: number;
}) {
  if (isQualified === undefined) {
    return (
      <Badge variant="outline" className="gap-1">
        <Clock className="w-3 h-3" />
        Pending
      </Badge>
    );
  }

  if (isQualified) {
    return (
      <Badge variant="success" className="gap-1">
        <CheckCircle2 className="w-3 h-3" />
        Qualified {score && `(${score}%)`}
      </Badge>
    );
  }

  return (
    <Badge variant="destructive" className="gap-1">
      <XCircle className="w-3 h-3" />
      Not Qualified
    </Badge>
  );
}

export function MatchScoreBadge({ score }: { score?: number | null }) {
  if (score === undefined || score === null) {
    return <span className="text-muted-foreground text-xs">&mdash;</span>;
  }

  const variant =
    score >= 70 ? "success" : score >= 40 ? "warning" : "destructive";
  return (
    <Badge variant={variant} className="font-mono">
      {Math.round(score)}%
    </Badge>
  );
}

export function DeadlineBadge({ deadline }: { deadline?: string }) {
  const days = daysUntilDeadline(deadline);
  const urgency = getDeadlineUrgency(deadline);

  if (days === null) return <span className="text-muted-foreground">&mdash;</span>;

  const colorClass =
    urgency === "urgent"
      ? "text-destructive"
      : urgency === "warning"
      ? "text-warning"
      : "text-foreground";

  return (
    <span className={cn("flex items-center gap-1", colorClass)}>
      {urgency === "urgent" && <AlertTriangle className="w-3 h-3" />}
      {days < 0 ? "Overdue" : days === 0 ? "Today" : `${days} days`}
    </span>
  );
}

export function parseRetryAfterSeconds(error: unknown): number | null {
  if (typeof error !== "object" || error === null) {
    return null;
  }

  const headers = (
    error as { response?: { headers?: Record<string, string | number> } }
  ).response?.headers;
  const headerValue = headers?.["retry-after"] ?? headers?.["Retry-After"];
  if (headerValue !== undefined) {
    const parsed = Number(headerValue);
    if (Number.isFinite(parsed) && parsed > 0) {
      return Math.ceil(parsed);
    }
    const headerDate = new Date(String(headerValue));
    if (!Number.isNaN(headerDate.getTime())) {
      const diffSeconds = Math.ceil((headerDate.getTime() - Date.now()) / 1000);
      if (diffSeconds > 0) {
        return diffSeconds;
      }
    }
  }

  const detail = getApiErrorDetail(error);
  if (!detail) {
    return null;
  }

  const detailMatch = detail.match(/retry in about\s+(\d+)\s+seconds/i);
  if (detailMatch) {
    return Number(detailMatch[1]);
  }

  return null;
}

export function formatSeconds(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

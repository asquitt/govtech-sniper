import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string to a human-readable format
 */
export function formatDate(dateString: string | undefined): string {
  if (!dateString) return "—";
  
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

/**
 * Format a date with time
 */
export function formatDateTime(dateString: string | undefined): string {
  if (!dateString) return "—";
  
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  
  return formatDate(dateString);
}

/**
 * Format file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Format currency
 */
export function formatCurrency(amount: number | undefined): string {
  if (amount === undefined) return "—";
  
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + "...";
}

/**
 * Get status color class
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    new: "badge-new",
    analyzing: "badge-analyzing",
    analyzed: "badge-ready",
    drafting: "badge-analyzing",
    ready: "badge-ready",
    submitted: "badge-ready",
    archived: "badge-error",
    pending: "badge-new",
    processing: "badge-analyzing",
    completed: "badge-ready",
    failed: "badge-error",
    error: "badge-error",
  };
  
  return colors[status.toLowerCase()] || "badge-new";
}

/**
 * Get importance color
 */
export function getImportanceColor(importance: string): string {
  const colors: Record<string, string> = {
    mandatory: "text-destructive",
    evaluated: "text-warning",
    optional: "text-muted-foreground",
    informational: "text-muted-foreground",
  };
  
  return colors[importance.toLowerCase()] || "text-foreground";
}

/**
 * Parse citation markers from text
 */
export interface ParsedCitation {
  sourceFile: string;
  pageNumber?: number;
  startIndex: number;
  endIndex: number;
  raw: string;
}

export function parseCitations(text: string): ParsedCitation[] {
  const pattern = /\[\[Source:\s*([^,\]]+)(?:,\s*[Pp]age\s*(\d+))?\]\]/g;
  const citations: ParsedCitation[] = [];
  
  let match;
  while ((match = pattern.exec(text)) !== null) {
    citations.push({
      sourceFile: match[1].trim(),
      pageNumber: match[2] ? parseInt(match[2], 10) : undefined,
      startIndex: match.index,
      endIndex: match.index + match[0].length,
      raw: match[0],
    });
  }
  
  return citations;
}

/**
 * Remove citation markers from text
 */
export function stripCitations(text: string): string {
  return text.replace(/\[\[Source:\s*[^\]]+\]\]/g, "").replace(/\s+/g, " ").trim();
}

/**
 * Calculate days until deadline
 */
export function daysUntilDeadline(deadline: string | undefined): number | null {
  if (!deadline) return null;
  
  const deadlineDate = new Date(deadline);
  const now = new Date();
  const diffMs = deadlineDate.getTime() - now.getTime();
  
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

/**
 * Get deadline urgency level
 */
export function getDeadlineUrgency(deadline: string | undefined): "urgent" | "warning" | "normal" | null {
  const days = daysUntilDeadline(deadline);
  
  if (days === null) return null;
  if (days < 0) return "urgent";
  if (days <= 3) return "urgent";
  if (days <= 7) return "warning";
  
  return "normal";
}


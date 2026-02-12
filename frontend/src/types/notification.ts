// =============================================================================
// Notification Types
// =============================================================================

export type NotificationType =
  | "deadline_reminder"
  | "rfp_match"
  | "analysis_complete"
  | "generation_complete"
  | "system_alert"
  | "team_invite"
  | "comment_added"
  | "mention";

export interface AppNotification {
  id: number;
  user_id: number;
  notification_type: NotificationType;
  title: string;
  message: string;
  channels: string[];
  is_read: boolean;
  is_sent: boolean;
  rfp_id: number | null;
  proposal_id: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  email_address: string | null;
  deadline_reminder: boolean;
  rfp_match: boolean;
  analysis_complete: boolean;
  generation_complete: boolean;
  system_alert: boolean;
  team_invite: boolean;
  comment_added: boolean;
  mention: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  slack_webhook_url: string | null;
  deadline_reminder_days: number[];
}

// =============================================================================
// Onboarding Types
// =============================================================================

export type OnboardingStepId =
  | "create_account"
  | "upload_rfp"
  | "analyze_rfp"
  | "upload_documents"
  | "create_proposal"
  | "export_proposal";

export interface OnboardingStep {
  id: OnboardingStepId;
  title: string;
  description: string;
  completed: boolean;
  completed_at: string | null;
  href: string;
}

export interface OnboardingProgress {
  steps: OnboardingStep[];
  completed_count: number;
  total_steps: number;
  is_complete: boolean;
  is_dismissed?: boolean;
}

// =============================================================================
// KB Intelligence Types
// =============================================================================

export interface FreshnessDocument {
  id: number;
  title: string;
  document_type: string;
  age_days: number;
  freshness: "fresh" | "aging" | "stale" | "outdated";
  last_updated: string;
  times_cited: number;
  last_cited_at: string | null;
}

export interface FreshnessReport {
  summary: Record<string, number>;
  total_documents: number;
  documents: FreshnessDocument[];
}

export interface GapAnalysis {
  type_coverage: Record<string, number>;
  type_gaps: { type: string; label: string; count: number }[];
  naics_codes_covered: number;
  agencies_covered: number;
  uncited_documents: { id: number; title: string; type: string }[];
  stale_past_performance: { id: number; title: string; age_years: number }[];
  recommendations: { type: string; message: string }[];
}

export interface DuplicateGroup {
  match_type: string;
  key: string;
  documents: { id: number; title: string; type?: string; size?: number }[];
}

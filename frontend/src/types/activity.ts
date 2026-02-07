export type ActivityType =
  | "section_edited"
  | "section_generated"
  | "review_scheduled"
  | "review_completed"
  | "comment_added"
  | "comment_resolved"
  | "member_joined"
  | "section_assigned"
  | "document_exported"
  | "status_changed";

export interface ActivityFeedEntry {
  id: number;
  proposal_id: number;
  user_id: number;
  activity_type: ActivityType;
  summary: string;
  section_id?: number | null;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
}

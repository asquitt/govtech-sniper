export type EventType = "industry_day" | "pre_solicitation" | "conference" | "webinar";

export interface IndustryEvent {
  id: number;
  user_id: number;
  title: string;
  agency?: string | null;
  event_type: EventType;
  date: string;
  location?: string | null;
  registration_url?: string | null;
  related_rfp_id?: number | null;
  description?: string | null;
  source?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface EventListResponse {
  events: IndustryEvent[];
  total: number;
}

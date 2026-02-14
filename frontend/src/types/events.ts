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

export interface EventIngestResponse {
  created: number;
  existing: number;
  candidates: number;
  created_event_ids: number[];
  source_breakdown: Record<string, number>;
}

export interface EventAlert {
  event: IndustryEvent;
  relevance_score: number;
  match_reasons: string[];
  days_until_event: number;
}

export interface EventAlertResponse {
  alerts: EventAlert[];
  total: number;
  evaluated: number;
}

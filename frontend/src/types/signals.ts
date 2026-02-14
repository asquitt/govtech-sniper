export type SignalType = "budget" | "award" | "news" | "congressional" | "recompete";

export type DigestFrequency = "daily" | "weekly";

export interface MarketSignal {
  id: number;
  user_id: number | null;
  title: string;
  signal_type: SignalType;
  agency?: string | null;
  content?: string | null;
  source_url?: string | null;
  relevance_score: number;
  published_at?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface SignalListResponse {
  signals: MarketSignal[];
  total: number;
}

export interface SignalSubscription {
  id: number;
  user_id: number;
  agencies: string[];
  naics_codes: string[];
  keywords: string[];
  email_digest_enabled: boolean;
  digest_frequency: DigestFrequency;
  created_at: string;
  updated_at: string;
}

export interface SignalCreatePayload {
  title: string;
  signal_type?: SignalType;
  agency?: string;
  content?: string;
  source_url?: string;
  relevance_score?: number;
  published_at?: string;
}

export interface SubscriptionPayload {
  agencies: string[];
  naics_codes: string[];
  keywords: string[];
  email_digest_enabled: boolean;
  digest_frequency: DigestFrequency;
}

export interface SignalIngestResponse {
  created: number;
  updated: number;
  skipped: number;
  source_breakdown: Record<string, number>;
}

export interface SignalRescoreResponse {
  updated: number;
  average_score: number;
}

export interface SignalDigestItem {
  signal_id: number;
  title: string;
  signal_type: SignalType;
  agency?: string | null;
  relevance_score: number;
  source_url?: string | null;
  published_at?: string | null;
}

export interface SignalDigestPreview {
  period_days: number;
  total_unread: number;
  included_count: number;
  type_breakdown: Record<string, number>;
  top_signals: SignalDigestItem[];
}

export interface SignalDigestSendResponse extends SignalDigestPreview {
  recipient_email: string;
  sent_at: string;
  simulated: boolean;
}

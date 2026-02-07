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

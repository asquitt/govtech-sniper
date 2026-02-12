export interface WebhookSubscription {
  id: number;
  name: string;
  target_url: string;
  secret: string | null;
  event_types: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookDelivery {
  id: number;
  subscription_id: number;
  event_type: string;
  payload: Record<string, unknown>;
  status: string;
  response_code: number | null;
  response_body: string | null;
  created_at: string;
  delivered_at: string | null;
}

export interface SecretItem {
  id: number;
  key: string;
  value: string;
  created_at: string;
  updated_at: string;
}

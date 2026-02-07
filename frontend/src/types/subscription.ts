// =============================================================================
// Subscription Types
// =============================================================================

export interface PlanFeature {
  name: string;
  included: boolean;
}

export interface PlanDefinition {
  tier: string;
  label: string;
  price_monthly: number; // cents
  price_yearly: number; // cents
  description: string;
  features: PlanFeature[];
  limits: Record<string, number>;
}

export interface UsageStats {
  rfps_used: number;
  rfps_limit: number;
  proposals_used: number;
  proposals_limit: number;
  api_calls_used: number;
  api_calls_limit: number;
}

export interface CheckoutSessionResponse {
  checkout_url: string;
  session_id: string;
}

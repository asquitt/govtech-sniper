export interface PipelineStageSummary {
  stage: string;
  count: number;
  unweighted_value: number;
  weighted_value: number;
}

export interface PipelineSummaryResponse {
  total_opportunities: number;
  total_unweighted: number;
  total_weighted: number;
  won_value: number;
  stages: PipelineStageSummary[];
}

export interface RevenueTimelinePoint {
  period: string;
  weighted_value: number;
  won_value: number;
  opportunity_count: number;
}

export interface RevenueTimelineResponse {
  granularity: string;
  points: RevenueTimelinePoint[];
}

export interface AgencyRevenueSummary {
  agency: string;
  opportunity_count: number;
  unweighted_value: number;
  weighted_value: number;
  won_value: number;
}

export interface AgencyRevenueResponse {
  agencies: AgencyRevenueSummary[];
  total_agencies: number;
}

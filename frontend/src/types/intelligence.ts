// =============================================================================
// Intelligence & Analytics Types
// =============================================================================

// Win/Loss Analysis
export interface AgencyWinLoss {
  agency: string;
  won: number;
  lost: number;
  win_rate: number;
  avg_win_value: number;
}

export interface SizeBucketWinLoss {
  bucket: string;
  won: number;
  lost: number;
  win_rate: number;
}

export interface DebriefSummary {
  id: number;
  outcome: string;
  source: string;
  debrief_date: string | null;
  win_themes: string[];
  loss_factors: string[];
  winning_vendor: string | null;
  winning_price: number | null;
  our_price: number | null;
  num_offerors: number | null;
  technical_score: number | null;
  agency_feedback: string | null;
}

export interface ThemeCount {
  theme: string;
  count: number;
}

export interface FactorCount {
  factor: string;
  count: number;
}

export interface Recommendation {
  type: "strength" | "warning" | "insight" | "action";
  title: string;
  message: string;
}

export interface WinLossAnalysis {
  by_agency: AgencyWinLoss[];
  by_size: SizeBucketWinLoss[];
  debriefs: DebriefSummary[];
  top_win_themes: ThemeCount[];
  top_loss_factors: FactorCount[];
  recommendations: Recommendation[];
}

// Budget Intelligence
export interface AgencySpendingYear {
  year: string;
  award_count: number;
  total_spend: number;
  avg_award: number;
}

export interface AgencySpending {
  agency: string;
  years: AgencySpendingYear[];
  total_spend: number;
}

export interface NaicsSpendingYear {
  year: string;
  count: number;
  total: number;
}

export interface NaicsSpending {
  naics_code: string;
  years: NaicsSpendingYear[];
  total_spend: number;
}

export interface BudgetSeasonMonth {
  month: number;
  rfp_count: number;
}

export interface CompetitorAward {
  vendor: string;
  wins: number;
  total_value: number;
  avg_value: number;
}

export interface BudgetIntelligenceData {
  top_agencies: AgencySpending[];
  top_naics: NaicsSpending[];
  budget_season: BudgetSeasonMonth[];
  top_competitors: CompetitorAward[];
}

// Pipeline Forecast
export interface ForecastPoint {
  period: string;
  weighted_value: number;
  optimistic_value: number;
  pessimistic_value: number;
  opportunity_count: number;
  unweighted_value: number;
}

export interface PipelineForecast {
  granularity: string;
  forecast: ForecastPoint[];
  total_weighted: number;
  total_unweighted: number;
}

// KPIs
export interface KPIData {
  win_rate: number;
  total_won: number;
  total_lost: number;
  active_pipeline: {
    count: number;
    unweighted_value: number;
    weighted_value: number;
  };
  won_revenue: {
    count: number;
    value: number;
  };
  active_proposals: number;
  avg_turnaround_days: number;
  upcoming_deadlines: number;
}

// Resource Allocation
export interface WorkloadItem {
  status: string;
  count: number;
}

export interface CaptureWorkloadItem {
  stage: string;
  count: number;
}

export interface ResourceAllocation {
  proposal_workload: WorkloadItem[];
  capture_workload: CaptureWorkloadItem[];
}

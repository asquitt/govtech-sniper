// =============================================================================
// Analytics Reporting Types
// =============================================================================

export interface WinRateTrend {
  month: string;
  won: number;
  lost: number;
  rate: number;
}

export interface WinRateData {
  win_rate: number;
  total_won: number;
  total_lost: number;
  trend: WinRateTrend[];
}

export interface PipelineStage {
  stage: string;
  count: number;
  total_value: number;
}

export interface PipelineByStageData {
  stages: PipelineStage[];
  total_pipeline_value: number;
}

export interface StageConversion {
  from_stage: string;
  to_stage: string;
  count_from: number;
  count_to: number;
  rate: number;
}

export interface ConversionRatesData {
  conversions: StageConversion[];
  overall_rate: number;
}

export interface TurnaroundPoint {
  month: string;
  avg_days: number;
  count: number;
}

export interface ProposalTurnaroundData {
  overall_avg_days: number;
  trend: TurnaroundPoint[];
}

export interface NAICSPerformanceEntry {
  naics_code: string;
  total: number;
  won: number;
  lost: number;
  win_rate: number;
}

export interface NAICSPerformanceData {
  entries: NAICSPerformanceEntry[];
}

export interface ExportRequest {
  report_type: string;
  format: string;
}

export type ReportType = "pipeline" | "proposals" | "revenue" | "activity";
export type ScheduleFrequency = "daily" | "weekly" | "monthly";

export interface ReportConfig {
  columns: string[];
  filters: Record<string, string>;
  group_by: string | null;
  sort_by: string | null;
  sort_order: "asc" | "desc";
}

export interface SavedReport {
  id: number;
  user_id: number;
  name: string;
  report_type: ReportType;
  config: ReportConfig;
  schedule: ScheduleFrequency | null;
  is_shared: boolean;
  shared_with_emails: string[];
  delivery_recipients: string[];
  delivery_enabled: boolean;
  delivery_subject: string | null;
  last_generated_at: string | null;
  last_delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SavedReportCreate {
  name: string;
  report_type: ReportType;
  config?: ReportConfig;
  schedule?: ScheduleFrequency | null;
  is_shared?: boolean;
  shared_with_emails?: string[];
  delivery_recipients?: string[];
  delivery_enabled?: boolean;
  delivery_subject?: string | null;
}

export interface SavedReportUpdate {
  name?: string;
  report_type?: ReportType;
  config?: ReportConfig;
  schedule?: ScheduleFrequency | null;
  is_shared?: boolean;
  shared_with_emails?: string[];
  delivery_recipients?: string[];
  delivery_enabled?: boolean;
  delivery_subject?: string | null;
}

export interface ReportDataResponse {
  columns: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
}

export interface ReportShareUpdate {
  is_shared: boolean;
  shared_with_emails: string[];
}

export interface ReportDeliveryScheduleUpdate {
  frequency: ScheduleFrequency;
  recipients: string[];
  enabled: boolean;
  subject?: string | null;
}

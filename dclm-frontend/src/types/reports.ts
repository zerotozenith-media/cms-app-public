export interface Service { id: number; name: string; }
export interface Department { id: number; name: string; }

export interface Testimony {
  id: number;
  member_name: string;
  is_anonymous: boolean;
  date: string;
  service: number;
  service_name: string;
  text: string;
}

export interface WeeklyNote {
  id: number;
  department: number;
  department_name: string;
  week_label: string;
  week_start: string;
  highlights: string;
  challenges: string;
  prayer_points: string;
}

export type ReportKind = 'overseer' | 'zonal';

export interface Report {
  location?: string | null;
  location_name?: string;
  id: number;
  kind: ReportKind;
  /** "Overseer report" or "Zonal monthly". */
  kind_label: string;
  start_month: number | null;
  start_year: number | null;
  period_month: number;
  period_year: number;
  /** "September 2026" or "July to September 2026". */
  period_label: string;
  summary: string;
  challenges: string;
  training: string;
  conclusion: string;
  generated_by: number;
  generated_by_name: string;
  generated_at: string;
  other_additions: string;
  pdf_file: string;
}

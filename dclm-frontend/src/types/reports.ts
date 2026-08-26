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

export interface Report {
  id: number;
  period_month: number;
  period_year: number;
  generated_by: number;
  generated_by_name: string;
  generated_at: string;
  other_additions: string;
  pdf_file: string;
}

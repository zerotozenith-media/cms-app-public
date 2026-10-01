/**
 * The dashboard summary. Each section is present only when the viewer
 * may see that module; otherwise it carries `*_access: false` so the page
 * can show a restricted state rather than an empty one.
 */

export type DashPeriod = 'this-month' | 'last-month' | 'this-year' | 'last-year' | string;

export interface AttendancePoint {
  date: string;
  adults: number;
  youth: number;
  children: number;
  online: number;
  total: number;
}

export interface GoalSummary {
  id: number;
  name: string;
  current: number;
  target: number;
  unit: string;
  pct: number;
  /** Stated in words, because colour alone had no key. */
  status: 'on-track' | 'behind' | 'attention';
  not_started: boolean;
  link_route: string;
  link_tab: string;
}

export interface DashboardSummary {
  follow_up_people?: { name: string; task: string; due_date: string; days_overdue: number; link: string }[];
  period: { start: string; end: string; label: string };
  banner: { message: string; has_outstanding: boolean };

  attendance_access: boolean;
  attendance?: {
    meeting_id: string | null;
    meeting_name: string;
    grouping?: 'month' | 'service';
    period?: { key: string; label: string };
    trend: AttendancePoint[];
    average: number;
    latest: number;
    target: number | null;
  };
  meetings?: { id: string; name: string }[];
  pending_sessions?: number;
  fellowships?: {
    groups: { name: string; attendance: number; meetings: number }[];
    meetings_held: number;
    offering: number;
  };

  finance_access: boolean;
  giving_total?: number;
  expense_total?: number;
  net_total?: number;
  giving_previous?: number;
  giving_change_pct?: number | null;
  giving_by_fund?: { fund: string; value: number }[];

  newcomers_access: boolean;
  newcomers_in_pipeline?: number;
  newcomers_registered?: number;
  unassigned_newcomers?: number;
  follow_ups?: {
    overdue: number;
    this_week: number;
    later: number;
    urgent: { newcomer_id: number; newcomer_name: string; text: string;
              due_date: string; days: number }[];
  };
  new_members?: { count: number; recent: { id: number; name: string; how: string }[] };
  enquiries_waiting?: {
    count: number;
    oldest: { id: number; name: string; source: string; days: number }[];
  };

  goals_access: boolean;
  short_term_goals?: GoalSummary[];

  testimonies_access: boolean;
  testimonies?: { count: number; recent: { text: string; by: string; service?: string; date: string }[] };
}

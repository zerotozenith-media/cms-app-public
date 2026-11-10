import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import { getViewingLocation } from './viewing';

/** The dashboard (redesign approved 10 November 2026), from /api/dashboard/. */
export type PeriodKey = 'this_month' | 'this_quarter' | 'this_year' | 'last_year' | 'last_month' | 'year' | 'range';
export interface PeriodChoice { period?: PeriodKey; year?: number; from?: string; to?: string }

export interface MonthMoney { month: string; giving: string; expenses: string; giving_last_year: string | null; so_far: boolean }
export interface CashRow {
  month: string; start: string; giving: string; expenses: string; remitted: string; net: string; cash: string;
  status: 'open' | 'sent' | 'closed'; status_label: string; so_far: boolean;
}
export interface LocationRow {
  id?: string; name: string; attendance?: number | null; attendance_change?: number | null; newcomers?: number;
  giving?: string; expenses?: string; net?: string; month_end?: string;
}
export interface MeetingRow {
  id: string; name: string; held: number; not_filled: number; attendance: number | null;
  attendance_change: number | null; offering?: string | null;
}
export type DashTable =
  | { by: 'location'; rows: LocationRow[]; total: LocationRow; month_end_month: string; columns: { attendance: boolean; newcomers: boolean; money: boolean } }
  | { by: 'meeting'; rows: MeetingRow[]; location: string; columns: { money: boolean } }
  | { by: 'month'; locations: { id: string; name: string; rows: CashRow[] }[] };

export interface Dashboard {
  kind: 'leader' | 'accounts' | 'worker';
  today: string; name: string;
  period: { key: PeriodKey; label: string; span: string; start: string; end: string };
  compare: { label: string; kind: 'year' | 'before' } | null;
  records_start: string;
  scope: { id: string; name: string } | null;
  access: Record<'attendance' | 'finance' | 'newcomers' | 'goals' | 'reports' | 'members', boolean>;
  receipt_flag_over: string;
  cards: {
    attendance?: { value: number | null; before: number | null; latest: { date: string; total: number } | null };
    giving?: { value: string; before: string | null };
    expenses?: { value: string; before: string | null };
    net?: { value: string };
    membership?: { on_track: number; ready: number; pipeline: number };
    cash?: { value: string; by_location: { name: string; value: string | null }[] };
    month_end?: { waiting: { location: string; month: string }[]; open: { location: string; month: string }[] };
    my_tasks?: { due: number; overdue: number; today: number };
    my_newcomers?: number;
  };
  charts: {
    money_by_month?: MonthMoney[];
    funds?: { fund: string; amount: number }[];
    expense_categories?: { top: { category: string; amount: number }[]; more: number };
    attendance_by_month?: { meeting: string; meetings: { id: string; name: string }[]; months: { month: string; attendance: number | null }[] };
    newcomers_by_month?: { month: string; newcomers: number }[];
  };
  newcomer_stats?: { pipeline: number; follow_ups_due: number };
  new_members?: { count: number; recent: { id: number; name: string; joined: string }[] };
  enquiries?: { count: number; oldest: { id: number; name: string; source: string; days: number }[] };
  follow_up_people?: { name: string; task: string; due_date: string; days_overdue: number; link: string }[];
  goals?: { id: number; name: string; current: number; target: number; pct: number; status: 'achieved' | 'on_track' | 'behind' | 'not_started' }[];
  testimonies?: { count: number; latest: { text: string; by: string; service: string; date: string } | null };
  fellowships?: { groups: { name: string; attendance: number; meetings: number }[]; meetings_held: number; offering: string };
  table?: DashTable;
  actions: string[];
}

function params(choice: PeriodChoice, meeting?: string) {
  const p: Record<string, string> = {};
  if (choice.period) p.period = choice.period;
  if (choice.period === 'year' && choice.year) p.year = String(choice.year);
  if (choice.period === 'range' && choice.from && choice.to) { p.from = choice.from; p.to = choice.to; }
  if (meeting) p.meeting = meeting;
  return p;
}

export function useDashboard(choice: PeriodChoice, meeting?: string) {
  return useQuery({
    queryKey: ['dashboard2', choice, meeting, getViewingLocation()],
    queryFn: async () => (await apiClient.get<Dashboard>('/dashboard/', { params: params(choice, meeting) })).data,
    placeholderData: (prev) => prev,
  });
}

/** Downloads the table as Excel or PDF through the signed-in client, so the
 *  file carries the same sign-in and viewing location as the page. */
export async function exportTable(choice: PeriodChoice, output: 'excel' | 'pdf', location?: string) {
  const p = { ...params(choice), output, ...(location ? { location } : {}) };
  const r = await apiClient.get('/dashboard/export/', { params: p, responseType: 'blob' });
  const cd = String(r.headers['content-disposition'] ?? '');
  const name = /filename="([^"]+)"/.exec(cd)?.[1] ?? `DCLM-dashboard.${output === 'excel' ? 'xlsx' : 'pdf'}`;
  const url = URL.createObjectURL(r.data as Blob);
  const a = document.createElement('a');
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/**
 * Month-end balance (Kay, 30 October 2026): balance the money held each
 * month, send it for approval, and close it. See finance/monthend_api.py.
 */
export interface MonthEndFigures {
  opening: string | null; opening_from: 'start' | 'previous' | 'missing';
  giving: string; giving_count: number;
  expenses: string; expenses_count: number;
  remittance: string; remittances: { month: string; sent_on: string; amount: string }[];
  expected: string | null;
}

export interface MonthEndRecord {
  status: 'open' | 'sent' | 'closed'; status_label: string;
  counted_amount: string | null; counted_by_1: string; counted_by_2: string;
  difference: string | null; difference_note: string; attachment: string | null;
  prepared_by: string; prepared_by_id: number | null; sent_at: string | null;
  approved_by: string; approved_at: string | null;
  sent_back_note: string; sent_back_by: string; sent_back_at: string | null;
  reopen_reason: string; reopened_by: string; reopened_at: string | null;
}

export interface MonthEndRow {
  month: string; label: string; status: 'open' | 'sent' | 'closed'; status_label: string;
  closing: string | null; difference: string | null; approved_by: string; approved_at: string | null;
}

export interface MonthEnd {
  location: { id: string; name: string };
  settings: { kept_as: 'cash' | 'bank'; kept_as_label: string; start_month: string; start_label: string; opening_balance: string };
  month: string; label: string; ended: boolean; last_day: string; before_start: boolean;
  figures: MonthEndFigures; record: MonthEndRecord | null; months: MonthEndRow[];
  latest_closed: string | null;
  can: { prepare: boolean; approve: boolean; reopen: boolean; settings: boolean };
  is_preparer: boolean;
}

export interface MoneySettings {
  location: { id: string; name: string };
  kept_as: 'cash' | 'bank'; start_month: string; opening_balance: string;
  locked: boolean; updated_by: string; updated_at: string | null;
}

const KEY = 'month-end';

export function useMonthEnd(location: string, month: string) {
  return useQuery({
    queryKey: [KEY, location, month],
    enabled: !!location,
    queryFn: async () => (await apiClient.get<MonthEnd>('/month-end/', { params: { location, month } })).data,
  });
}

function useAct<T>(path: string, multipart = false) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: T) => (await apiClient.post<MonthEnd>(path, body,
      multipart ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined)).data,
    onSuccess: (data) => {
      qc.setQueryData([KEY, data.location.id, data.month], data);
      qc.invalidateQueries({ queryKey: [KEY] });
    },
  });
}

export const useSendMonthEnd = () => useAct<FormData>('/month-end/send/', true);
export const useApproveMonthEnd = () => useAct<{ location: string; month: string }>('/month-end/approve/');
export const useSendBackMonthEnd = () => useAct<{ location: string; month: string; note: string }>('/month-end/send-back/');
export const useReopenMonthEnd = () => useAct<{ location: string; month: string; reason: string }>('/month-end/reopen/');

export function useMoneySettings(location: string) {
  return useQuery({
    queryKey: ['money-settings', location],
    enabled: !!location,
    queryFn: async () => (await apiClient.get<MoneySettings>('/money-settings/', { params: { location } })).data,
  });
}

export function useSaveMoneySettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ location, ...body }: { location: string; kept_as: string; start_month?: string; opening_balance?: string }) =>
      (await apiClient.put<MoneySettings>('/money-settings/', body, { params: { location } })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['money-settings'] }); qc.invalidateQueries({ queryKey: [KEY] }); },
  });
}

/** BHD to the fils (three decimal places), so a balance that is out by
 *  5 fils shows it. Reports round to two places. */
export function bhd(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === '') return '-';
  return `BHD ${Number(v).toLocaleString('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}`;
}

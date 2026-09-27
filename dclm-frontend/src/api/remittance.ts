/**
 * Monthly remittance.
 *
 * The system works out what should be sent, which is what a month
 * collected less what it spent. The person recording it can override
 * that, because a member sometimes covers the expenses and more goes
 * than the arithmetic says. Both figures are kept.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';

export type RemitDestination = 'dubai' | 'lagos' | 'qatar' | 'kept';

export const REMIT_DESTINATIONS: { value: RemitDestination; label: string }[] = [
  { value: 'dubai', label: 'Dubai' },
  { value: 'lagos', label: 'Lagos' },
  { value: 'qatar', label: 'Qatar' },
  { value: 'kept', label: 'Kept here' },
];

export interface RemittanceLine {
  id?: number;
  fund: number;
  fund_name?: string;
  amount_due: string;
  amount_sent: string;
  destination: RemitDestination;
  difference?: string;
}

export interface Remittance {
  id: number;
  month: string;
  sent_on: string;
  reference: string;
  note: string;
  lines: RemittanceLine[];
  total_due: string;
  total_sent: string;
  difference: string;
  recorded_by_name?: string;
  recorded_at?: string;
}

export interface RemittanceProposal {
  month: string;
  collected: string;
  expenses: string;
  due: string;
  lines: RemittanceLine[];
  already_recorded: number | null;
}

/** Each location sends its own money, so remittances are per location.
 *  Somebody limited to one location always gets their own; the server
 *  ignores the choice for them. */
export function useRemittances(location?: string) {
  return useQuery({
    queryKey: ['remittances', location ?? ''],
    queryFn: async () =>
      (await apiClient.get<PaginatedResponse<Remittance>>('/remittances/', {
        params: location ? { location } : {} })).data.results,
  });
}

/** What the month should send, worked out from its own records. */
export function useRemittanceProposal(month: string | null, location?: string) {
  return useQuery({
    queryKey: ['remittance-proposal', month, location ?? ''],
    enabled: !!month,
    queryFn: async () =>
      (await apiClient.get<RemittanceProposal>('/remittances/proposed/', {
        params: { month, ...(location ? { location } : {}) } })).data,
  });
}

export function useSaveRemittance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: Partial<Remittance> & { id?: number }) =>
      id
        ? (await apiClient.patch<Remittance>(`/remittances/${id}/`, payload)).data
        : (await apiClient.post<Remittance>('/remittances/', payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['remittances'] });
      qc.invalidateQueries({ queryKey: ['remittance-proposal'] });
    },
  });
}

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface OutstandingItem {
  key: string;
  count: number;
  level: 'overdue' | 'waiting';
  label: string;
  link: string;
}
export interface Outstanding { items: OutstandingItem[]; total: number; level: 'overdue' | 'waiting' | null }

/** Everything waiting on this person. One source for the bell (F4) and the
 *  dashboard's "Needs your attention" card (F5), so they always agree. */
export function useOutstanding() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await apiClient.get<Outstanding>('/notifications/')).data,
    refetchInterval: 120_000, staleTime: 60_000,
  });
}

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { DashboardSummary } from '../types/dashboard';

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: async () => {
      const resp = await apiClient.get<DashboardSummary>('/dashboard/summary/');
      return resp.data;
    },
  });
}

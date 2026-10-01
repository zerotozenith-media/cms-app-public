import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { DashboardSummary, DashPeriod } from '../types/dashboard';

/** One period and one meeting for the whole page, so the cards never
 *  disagree about which month or which meeting they describe. */
export function useDashboardSummary(period: DashPeriod = 'this-month', meeting = 'fri-worship', chartPeriod: DashPeriod = 'this-year') {
  return useQuery({
    queryKey: ['dashboard-summary', period, meeting, chartPeriod],
    queryFn: async () =>
      (await apiClient.get<DashboardSummary>('/dashboard/summary/', {
        params: { period, meeting, chart_period: chartPeriod },
      })).data,
  });
}

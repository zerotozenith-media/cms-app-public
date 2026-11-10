import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** Church-wide switches an admin controls. Currently just the one, but
 *  shaped as a generic key/value store so more can be added without a
 *  new endpoint each time. */
export interface AppSettings {
  auto_assign_newcomers: boolean;
  // Admin, Settings (10 November 2026)
  finance_year_end_month: number;
  records_start: string;
  receipt_flag_over: string;
  dashboard_opens_on: 'this_month' | 'this_quarter' | 'this_year' | 'last_year';
  two_step_remember_days: number;
  two_step_roles: { id: number; name: string; two_step: 'required' | 'choose' | 'off' }[];
}
export type AppSettingsPatch = Partial<Omit<AppSettings, 'two_step_roles'>> & { two_step_roles?: Record<string, string> };

export function useAppSettings() {
  return useQuery({
    queryKey: ['app-settings'],
    queryFn: async () => (await apiClient.get<AppSettings>('/settings/')).data,
  });
}

export function useUpdateAppSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AppSettingsPatch) =>
      (await apiClient.patch<AppSettings>('/settings/', payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['app-settings'] });
      qc.invalidateQueries({ queryKey: ['dashboard2'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** Church-wide switches an admin controls. Currently just the one, but
 *  shaped as a generic key/value store so more can be added without a
 *  new endpoint each time. */
export interface AppSettings {
  auto_assign_newcomers: boolean;
}

export function useAppSettings() {
  return useQuery({
    queryKey: ['app-settings'],
    queryFn: async () => (await apiClient.get<AppSettings>('/settings/')).data,
  });
}

export function useUpdateAppSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<AppSettings>) =>
      (await apiClient.patch<AppSettings>('/settings/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['app-settings'] }),
  });
}

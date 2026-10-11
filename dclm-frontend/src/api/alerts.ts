import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface AlertKind { key: string; label: string; help: string; on: boolean }
export interface AlertSettings { kinds: AlertKind[]; devices: number; this_device: boolean }
export interface SentAlert { id: number; title: string; body: string; audience: string; location: string; sent_by: string; people: number; devices: number; created_at: string }

export function useAlertSettings(endpoint: string | null) {
  return useQuery({
    queryKey: ['alert-settings', endpoint ?? ''],
    queryFn: async () => (await apiClient.get<AlertSettings>('/alerts/settings/', { params: endpoint ? { endpoint } : {} })).data,
  });
}

export function useSaveAlertKind() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (change: Record<string, boolean>) => (await apiClient.patch<AlertSettings>('/alerts/settings/', change)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert-settings'] }),
  });
}

export function useTestAlert() {
  return useMutation({ mutationFn: async () => (await apiClient.post<{ devices: number }>('/alerts/test/')).data });
}

export function useSentAlerts(enabled: boolean) {
  return useQuery({
    queryKey: ['sent-alerts'], enabled,
    queryFn: async () => (await apiClient.get<{ people_with_alerts: number; results: SentAlert[] }>('/alerts/announcements/')).data,
  });
}

export function useSendAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { title: string; body: string; audience: string; location: string }) =>
      (await apiClient.post<{ id: number; people: number; devices: number }>('/alerts/announcements/', body)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sent-alerts'] }),
  });
}

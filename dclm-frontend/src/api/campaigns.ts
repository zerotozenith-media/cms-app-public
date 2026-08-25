import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Campaign, CampaignSummary } from '../types/campaigns';

export function useCampaigns() {
  return useQuery({
    queryKey: ['campaigns'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<Campaign> | Campaign[]>('/campaigns/');
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
    // A role without outreach permission gets 403; that is expected, not
    // an error worth retrying.
    retry: false,
  });
}

export function useCampaignSummary() {
  return useQuery({
    queryKey: ['campaign-summary'],
    queryFn: async () => (await apiClient.get<CampaignSummary>('/campaigns/summary/')).data,
    retry: false,
  });
}

export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Campaign>) =>
      (await apiClient.post<Campaign>('/campaigns/', payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['campaign-summary'] });
    },
  });
}

export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/campaigns/${id}/`); },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['campaign-summary'] });
    },
  });
}

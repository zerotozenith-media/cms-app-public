import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Goal } from '../types/goals';

/** Goals are a small, curated, admin-managed list , 14 approved goals,
 * not expected to grow into the hundreds the way attendance sessions or
 * giving records do. A single bounded fetch is genuinely appropriate
 * here, unlike the dedicated stats endpoints the last three batches
 * needed for unbounded data. */
export function useGoals() {
  return useQuery({
    queryKey: ['goals'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<Goal>>('/goals/', { params: { page_size: 100 } });
      return resp.data.results;
    },
  });
}

export function useCreateGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; horizon: string; target: number; unit: string }) =>
      (await apiClient.post<Goal>('/goals/', {
        ...payload,
        tracking: 'manual',
        // Matches the demo's createGoal() exactly , the user is never
        // asked for this; a sensible default is supplied automatically
        // for every manually-created goal.
        source: 'Manually tracked. Update the progress value as it changes.',
      })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });
}

export function useUpdateGoalProgress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, current }: { id: number; current: number }) =>
      (await apiClient.patch<Goal>(`/goals/${id}/`, { current })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });
}

export function useDeleteGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/goals/${id}/`); },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });
}

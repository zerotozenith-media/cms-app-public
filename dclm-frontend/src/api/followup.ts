import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type {
  MemberFollowUpTask, CompleteFollowUpPayload, FollowUpStats,
  AssignmentPreview, AssignmentApplyResult, AssignmentChange,
} from '../types/members';

/* ---- Member follow-up tasks ---- */

export interface FollowUpFilters {
  member?: number;
  assigned_to?: number;
  /** Omit to get both. The UI's Open / Completed / All filter maps here. */
  done?: boolean;
  ordering?: string;
}

export function useMemberFollowUpTasks(filters: FollowUpFilters = {}) {
  return useQuery({
    queryKey: ['member-followup-tasks', filters],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (filters.member !== undefined) params.member = String(filters.member);
      if (filters.assigned_to !== undefined) params.assigned_to = String(filters.assigned_to);
      if (filters.done !== undefined) params.done = String(filters.done);
      params.ordering = filters.ordering ?? 'due_date';
      params.page_size = '100';
      const resp = await apiClient.get<PaginatedResponse<MemberFollowUpTask>>(
        '/member-followup-tasks/', { params },
      );
      return resp.data.results;
    },
  });
}

export function useFollowUpStats() {
  return useQuery({
    queryKey: ['member-followup-stats'],
    queryFn: async () =>
      (await apiClient.get<FollowUpStats>('/member-followup-tasks/stats/')).data,
  });
}

/** The only way to mark a task done. The backend rejects the request
 *  unless all four outcome fields are filled, so a completed task always
 *  carries a real record of what happened. */
export function useCompleteFollowUpTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: CompleteFollowUpPayload }) =>
      (await apiClient.post<MemberFollowUpTask>(`/member-followup-tasks/${id}/complete/`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['member-followup-tasks'] });
      qc.invalidateQueries({ queryKey: ['member-followup-stats'] });
    },
  });
}

export function useDeleteFollowUpTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/member-followup-tasks/${id}/`); },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['member-followup-tasks'] });
      qc.invalidateQueries({ queryKey: ['member-followup-stats'] });
    },
  });
}

/* ---- Shepherd assignment ----
   Preview and apply are deliberately separate calls. The preview writes
   nothing, so an admin can review every proposed change before any of it
   is committed. */

export function useAssignmentPreview(reassignEveryone: boolean, enabled: boolean) {
  return useQuery({
    queryKey: ['assignment-preview', reassignEveryone],
    enabled,
    // Always refetch: the proposal depends on current shepherd loads,
    // which change as soon as anything else is assigned.
    staleTime: 0,
    gcTime: 0,
    retry: false,
    queryFn: async () =>
      (await apiClient.get<AssignmentPreview>('/members/assign-shepherds/', {
        params: reassignEveryone ? { reassign_everyone: 'true' } : {},
      })).data,
  });
}

export function useApplyAssignment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (changes: AssignmentChange[]) =>
      (await apiClient.post<AssignmentApplyResult>('/members/assign-shepherds/', { changes })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] });
      qc.invalidateQueries({ queryKey: ['newcomers'] });
      qc.invalidateQueries({ queryKey: ['assignment-preview'] });
    },
  });
}

export function useBulkAssignShepherd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ memberIds, shepherdId }: { memberIds: number[]; shepherdId: number }) =>
      (await apiClient.post<{ updated: number; shepherd: string }>(
        '/members/bulk-assign-shepherd/', { member_ids: memberIds, shepherd_id: shepherdId },
      )).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['members'] });
      qc.invalidateQueries({ queryKey: ['assignment-preview'] });
    },
  });
}

export interface EligibleShepherd {
  id: number;
  name: string;
}

/** Who the bulk-assign dropdown may offer. Comes from the same source
 *  the auto-assign engine uses, so the dropdown can never list someone
 *  the API would then reject. */
export function useEligibleShepherds() {
  return useQuery({
    queryKey: ['eligible-shepherds'],
    queryFn: async () =>
      (await apiClient.get<EligibleShepherd[]>('/members/eligible-shepherds/')).data,
  });
}

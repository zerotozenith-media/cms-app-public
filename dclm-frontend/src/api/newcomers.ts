import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient, API_BASE_URL } from './client';
import axios from 'axios';
import type { PaginatedResponse } from '../types/members';
import type { Newcomer, NewcomerTask, NewcomerSource, MilestoneType } from '../types/newcomers';
import type { CompleteFollowUpPayload } from '../types/members';

interface NewcomerListParams {
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export function useNewcomers(params: NewcomerListParams = {}) {
  return useQuery({
    queryKey: ['newcomers', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Newcomer>>('/newcomers/', { params })).data,
  });
}

/** Full unpaginated list for the kanban board, which needs every active
 * record grouped by stage, not one page at a time. */
export function useAllNewcomers() {
  return useQuery({
    queryKey: ['newcomers-all'],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Newcomer>>('/newcomers/', { params: { page_size: 100 } })).data.results,
  });
}

export function useNewcomer(id: number | undefined) {
  return useQuery({
    queryKey: ['newcomer', id],
    queryFn: async () => (await apiClient.get<Newcomer>(`/newcomers/${id}/`)).data,
    enabled: id !== undefined,
  });
}

export function useNewcomerSources() {
  return useQuery({
    queryKey: ['newcomer-sources'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<NewcomerSource> | NewcomerSource[]>('/newcomer-sources/');
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}

export function useMilestoneTypes() {
  return useQuery({
    queryKey: ['milestone-types'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<MilestoneType> | MilestoneType[]>('/milestone-types/');
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}

export function useNewcomerTasks(newcomerId: number) {
  return useQuery({
    queryKey: ['newcomer-tasks', newcomerId],
    queryFn: async () => (await apiClient.get<PaginatedResponse<NewcomerTask>>('/newcomer-tasks/', {
      params: { newcomer: newcomerId, page_size: 50 },
    })).data.results,
  });
}

function invalidateNewcomer(queryClient: ReturnType<typeof useQueryClient>, id: number) {
  queryClient.invalidateQueries({ queryKey: ['newcomer', id] });
  queryClient.invalidateQueries({ queryKey: ['newcomers'] });
  queryClient.invalidateQueries({ queryKey: ['newcomers-all'] });
  queryClient.invalidateQueries({ queryKey: ['newcomer-tasks', id] });
  // The aggregate Follow-up tab lists every newcomer's tasks, so it has
  // to refresh too. Without this a task completed from that screen stays
  // on screen until a manual reload, which reads as the save failing.
  queryClient.invalidateQueries({ queryKey: ['all-newcomer-tasks'] });
}

export function useCreateNewcomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.post<Newcomer>('/newcomers/', payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['newcomers'] });
      queryClient.invalidateQueries({ queryKey: ['newcomers-all'] });
    },
  });
}

export function useUpdateNewcomer(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.patch<Newcomer>(`/newcomers/${id}/`, payload)).data,
    onSuccess: () => invalidateNewcomer(queryClient, id),
  });
}

export function useDeleteNewcomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/newcomers/${id}/`); },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['newcomers'] });
      queryClient.invalidateQueries({ queryKey: ['newcomers-all'] });
    },
  });
}

export function useChangeStage(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { to_stage: string; note?: string }) =>
      (await apiClient.post<Newcomer>(`/newcomers/${id}/change-stage/`, payload)).data,
    onSuccess: () => invalidateNewcomer(queryClient, id),
  });
}

/** The kanban board drags a variable card each time, so the target id
 * isn't known when the component mounts , unlike useChangeStage above,
 * which is correct for the profile page's single, fixed newcomer. Hooks
 * can't be called with a dynamic id inside an event handler, so this
 * takes {id, to_stage} as mutate() arguments instead. */
export function useChangeStageForAnyNewcomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, to_stage }: { id: number; to_stage: string }) =>
      (await apiClient.post<Newcomer>(`/newcomers/${id}/change-stage/`, { to_stage })).data,
    onSuccess: (_data, variables) => invalidateNewcomer(queryClient, variables.id),
  });
}

export function useSetMilestone(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { milestone_type: number; achieved: boolean; achieved_date?: string }) =>
      (await apiClient.post<Newcomer>(`/newcomers/${id}/set-milestone/`, payload)).data,
    onSuccess: () => invalidateNewcomer(queryClient, id),
  });
}

export function useCreateTask(newcomerId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { text: string; due_date: string; assigned_to?: number }) =>
      (await apiClient.post<NewcomerTask>('/newcomer-tasks/', { ...payload, newcomer: newcomerId })).data,
    onSuccess: () => invalidateNewcomer(queryClient, newcomerId),
  });
}

/**
 * Marking a newcomer task done goes through this, not a plain PATCH.
 * `done` is read-only on the API precisely so a task cannot be ticked
 * without a record of what happened, and the four outcome fields are
 * all required. A PATCH of { done: true } silently changes nothing,
 * which is worse than an error, so that route is closed here too.
 */
export function useCompleteNewcomerTask(newcomerId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: CompleteFollowUpPayload }) =>
      (await apiClient.post<NewcomerTask>(`/newcomer-tasks/${id}/complete/`, payload)).data,
    onSuccess: () => invalidateNewcomer(queryClient, newcomerId),
  });
}

/** Edits the task itself (text, due date, assignee). Deliberately cannot
 *  touch `done` or the outcome fields; use useCompleteNewcomerTask. */
export function useUpdateTask(newcomerId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number; text?: string; due_date?: string; assigned_to?: number | null }) =>
      (await apiClient.patch<NewcomerTask>(`/newcomer-tasks/${id}/`, payload)).data,
    onSuccess: () => invalidateNewcomer(queryClient, newcomerId),
  });
}

export function useDeleteTask(newcomerId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/newcomer-tasks/${id}/`); },
    onSuccess: () => invalidateNewcomer(queryClient, newcomerId),
  });
}

/** The real public self-registration submission , deliberately uses a
 * bare axios call, not the shared apiClient, since this must never
 * attach a JWT token (there isn't one) and must never trigger the
 * authenticated refresh-on-401 interceptor logic. */
export async function submitPublicRegistration(payload: Record<string, unknown>) {
  const resp = await axios.post(`${API_BASE_URL}/public/newcomer-registration/`, payload);
  return resp.data;
}

/**
 * Every newcomer task across the pipeline, for the aggregate Follow-up
 * tab. Separate from useNewcomerTasks, which is scoped to one person's
 * profile: a leader wants one list of what is waiting, not to open each
 * newcomer in turn to find out.
 */
export function useAllNewcomerTasks(params: { done?: boolean; ordering?: string } = {}) {
  return useQuery({
    queryKey: ['all-newcomer-tasks', params],
    queryFn: async () => {
      const query: Record<string, string> = { page_size: '200' };
      if (params.done !== undefined) query.done = String(params.done);
      query.ordering = params.ordering ?? 'due_date';
      const resp = await apiClient.get<PaginatedResponse<NewcomerTask>>('/newcomer-tasks/', { params: query });
      return resp.data.results;
    },
  });
}

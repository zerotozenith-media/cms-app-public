import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type {
  Enquiry, EnquirySource, EnquiryTask, EnquiryStats, EnquiryStage,
} from '../types/enquiries';
import type { CompleteFollowUpPayload } from '../types/members';

function invalidateEnquiries(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['enquiries'] });
  qc.invalidateQueries({ queryKey: ['enquiry'] });
  qc.invalidateQueries({ queryKey: ['enquiry-stats'] });
}

export function useEnquiries(params: { stage?: string; source?: number; search?: string } = {}) {
  return useQuery({
    queryKey: ['enquiries', params],
    queryFn: async () => {
      const query: Record<string, string> = { page_size: '200' };
      if (params.stage) query.stage = params.stage;
      if (params.source !== undefined) query.source = String(params.source);
      if (params.search) query.search = params.search;
      const resp = await apiClient.get<PaginatedResponse<Enquiry>>('/enquiries/', { params: query });
      return resp.data.results;
    },
  });
}

export function useEnquiry(id: number | undefined) {
  return useQuery({
    queryKey: ['enquiry', id],
    enabled: id !== undefined,
    queryFn: async () => (await apiClient.get<Enquiry>(`/enquiries/${id}/`)).data,
  });
}

export function useEnquirySources() {
  return useQuery({
    queryKey: ['enquiry-sources'],
    queryFn: async () => (await apiClient.get<EnquirySource[]>('/enquiry-sources/')).data,
  });
}

export function useEnquiryStats() {
  return useQuery({
    queryKey: ['enquiry-stats'],
    queryFn: async () => (await apiClient.get<EnquiryStats>('/enquiries/stats/')).data,
  });
}

export function useCreateEnquiry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Enquiry>) =>
      (await apiClient.post<Enquiry>('/enquiries/', payload)).data,
    onSuccess: () => invalidateEnquiries(qc),
  });
}

export function useUpdateEnquiry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: Partial<Enquiry> & { id: number }) =>
      (await apiClient.patch<Enquiry>(`/enquiries/${id}/`, payload)).data,
    onSuccess: () => invalidateEnquiries(qc),
  });
}

/** Stage moves go through this, not a plain PATCH, so the change is
 *  recorded in the enquiry's history at the same time. */
export function useChangeEnquiryStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, stage, note }: { id: number; stage: EnquiryStage; note?: string }) =>
      (await apiClient.post<Enquiry>(`/enquiries/${id}/change-stage/`, { stage, note: note ?? '' })).data,
    onSuccess: () => invalidateEnquiries(qc),
  });
}

/** They attended. Creates the linked Newcomer and keeps the enquiry, so
 *  "how many online enquiries became people in the room" stays answerable. */
export function useConvertEnquiry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, location }: { id: number; location: string }) =>
      (await apiClient.post<Enquiry>(`/enquiries/${id}/convert/`, { location })).data,
    onSuccess: () => {
      invalidateEnquiries(qc);
      qc.invalidateQueries({ queryKey: ['newcomers'] });
    },
  });
}

export function useDeleteEnquiry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/enquiries/${id}/`); },
    onSuccess: () => invalidateEnquiries(qc),
  });
}

/* ---- Tasks ---- */

export function useEnquiryTasks(params: { enquiry?: number; done?: boolean } = {}) {
  return useQuery({
    queryKey: ['enquiry-tasks', params],
    queryFn: async () => {
      const query: Record<string, string> = { page_size: '200' };
      if (params.enquiry !== undefined) query.enquiry = String(params.enquiry);
      if (params.done !== undefined) query.done = String(params.done);
      const resp = await apiClient.get<PaginatedResponse<EnquiryTask>>('/enquiry-tasks/', { params: query });
      return resp.data.results;
    },
  });
}

export function useCreateEnquiryTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { enquiry: number; text: string; due_date: string }) =>
      (await apiClient.post<EnquiryTask>('/enquiry-tasks/', payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['enquiry-tasks'] });
      invalidateEnquiries(qc);
    },
  });
}

/** The only way to mark a task done. The API rejects it unless all four
 *  outcome fields are filled. */
export function useCompleteEnquiryTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: CompleteFollowUpPayload }) =>
      (await apiClient.post<EnquiryTask>(`/enquiry-tasks/${id}/complete/`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['enquiry-tasks'] });
      invalidateEnquiries(qc);
    },
  });
}

export function useDeleteEnquiryTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/enquiry-tasks/${id}/`); },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['enquiry-tasks'] });
      invalidateEnquiries(qc);
    },
  });
}

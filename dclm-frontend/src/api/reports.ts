import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Service, Department, Testimony, WeeklyNote, Report } from '../types/reports';

function useSimpleList<T>(key: string, url: string) {
  return useQuery({
    queryKey: [key],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<T> | T[]>(url);
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}

export const useServices = () => useSimpleList<Service>('services', '/services/');
export const useDepartments = () => useSimpleList<Department>('departments', '/departments/');

interface TestimonyListParams { service?: string; ordering?: string; page?: number; page_size?: number; }
export function useTestimonies(params: TestimonyListParams) {
  return useQuery({
    queryKey: ['testimonies', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Testimony>>('/testimonies/', { params })).data,
  });
}
export function useCreateTestimony() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.post<Testimony>('/testimonies/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['testimonies'] }),
  });
}
export function useUpdateTestimony() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      (await apiClient.patch<Testimony>(`/testimonies/${id}/`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['testimonies'] }),
  });
}
export function useDeleteTestimony() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/testimonies/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['testimonies'] }),
  });
}

interface WeeklyNoteListParams { department?: string; ordering?: string; page?: number; page_size?: number; }
export function useWeeklyNotes(params: WeeklyNoteListParams) {
  return useQuery({
    queryKey: ['weekly-notes', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<WeeklyNote>>('/weekly-notes/', { params })).data,
  });
}
export function useCreateWeeklyNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.post<WeeklyNote>('/weekly-notes/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['weekly-notes'] }),
  });
}
export function useUpdateWeeklyNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      (await apiClient.patch<WeeklyNote>(`/weekly-notes/${id}/`, payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['weekly-notes'] }),
  });
}
export function useDeleteWeeklyNote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/weekly-notes/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['weekly-notes'] }),
  });
}

export function useReports() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Report>>('/reports/', { params: { page_size: 20 } })).data,
  });
}
export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { period_month: number; period_year: number; other_additions: string }) =>
      (await apiClient.post<Report>('/reports/generate/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}
export function useDeleteReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/reports/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports'] }),
  });
}

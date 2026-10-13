import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Service, Department, Testimony, WeeklyNote, Report, ReportKind } from '../types/reports';

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
export interface ReportRequest {
  kind: ReportKind;
  from_year: number; from_month: number; to_year: number; to_month: number;
  location?: string;
  summary?: string; challenges?: string; training?: string; conclusion?: string;
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReportRequest) =>
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

/** What was written in the last overseer report for these figures. */
export function useLastReportText(location: string, enabled: boolean) {
  return useQuery({
    queryKey: ['reports', 'last-text', location],
    enabled,
    queryFn: async () => (await apiClient.get<{ summary: string; challenges: string; training: string; conclusion: string; from_report: string }>(
      '/reports/last-text/', { params: location ? { location } : {} })).data,
  });
}

/** The report as it would come out, without saving it. Returns a link to
 *  the PDF for opening in a new tab. */
export async function previewReport(payload: ReportRequest): Promise<{ url: string; filename: string }> {
  const resp = await apiClient.post('/reports/preview/', payload, { responseType: 'blob' });
  const disposition = String((resp.headers as Record<string, string>)['content-disposition'] ?? '');
  return {
    url: URL.createObjectURL(new Blob([resp.data as BlobPart], { type: 'application/pdf' })),
    filename: /filename="?([^"]+)"?/.exec(disposition)?.[1] || 'DCLM-Bahrain-report-preview.pdf',
  };
}

/** The zonal report's tables as a spreadsheet, for whoever at Zonal
 *  combines several locations and would otherwise retype the figures. */
export async function downloadZonalSpreadsheet(from: string, to: string, location?: string) {
  const resp = await apiClient.get('/reports/spreadsheet/', {
    params: { from, to, ...(location ? { location } : {}) }, responseType: 'blob',
  });
  const url = URL.createObjectURL(resp.data as Blob);
  const a = document.createElement('a');
  a.href = url;
  // The server names the file after the figures it actually sent, which
  // for somebody limited to one location is theirs, whatever was asked.
  const disposition = String((resp.headers as Record<string, string>)['content-disposition'] ?? '');
  a.download = /filename="?([^"]+)"?/.exec(disposition)?.[1] || `DCLM-Bahrain-Zonal-${from}-to-${to}.xlsx`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

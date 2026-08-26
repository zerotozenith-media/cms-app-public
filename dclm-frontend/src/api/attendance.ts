import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type {
  MeetingType, AttendanceSession, AttendanceStats, RecordAttendancePayload,
  AttendanceSessionMember, CheckInMode,
} from '../types/attendance';

export function useMeetingTypes(options: { enabled?: boolean } = {}) {
  return useQuery({
    enabled: options.enabled ?? true,
    queryKey: ['meeting-types'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<MeetingType> | MeetingType[]>('/meeting-types/');
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}

export function useCreateMeetingType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name: string; day: string; frequency: string; detail_level: string }) =>
      (await apiClient.post<MeetingType>('/meeting-types/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meeting-types'] }),
  });
}

export function useDeleteMeetingType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => { await apiClient.delete(`/meeting-types/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['meeting-types'] }),
  });
}

export function useAttendanceStats() {
  return useQuery({
    queryKey: ['attendance-stats'],
    queryFn: async () => (await apiClient.get<AttendanceStats>('/attendance-sessions/stats/')).data,
  });
}

interface SessionListParams {
  meeting_type?: string;
  status?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}

export function useSessions(params: SessionListParams) {
  return useQuery({
    queryKey: ['sessions', params],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<AttendanceSession>>('/attendance-sessions/', { params });
      return resp.data;
    },
  });
}

/** Latest filled sessions for a specific meeting type, for the age-group
 * trend chart , a small, already-bounded fetch, unlike the stat-row
 * counts, so no dedicated aggregation endpoint is needed here. */
export function useRecentFilledSessions(meetingTypeId: string, count = 6) {
  return useQuery({
    queryKey: ['recent-sessions', meetingTypeId, count],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<AttendanceSession>>('/attendance-sessions/', {
        params: { meeting_type: meetingTypeId, status: 'filled', ordering: '-date', page_size: count },
      });
      return resp.data.results.slice().reverse(); // oldest-to-newest for the chart
    },
  });
}

export function useSession(id: number | undefined) {
  return useQuery({
    queryKey: ['session', id],
    queryFn: async () => (await apiClient.get<AttendanceSession>(`/attendance-sessions/${id}/`)).data,
    enabled: id !== undefined,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { meeting_type: string; date: string; location: string; mode: string }) => {
      const resp = await apiClient.post<AttendanceSession>('/attendance-sessions/', payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['attendance-stats'] });
    },
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/attendance-sessions/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['attendance-stats'] });
    },
  });
}

export function useRecordSession(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RecordAttendancePayload) => {
      const resp = await apiClient.post<AttendanceSession>(`/attendance-sessions/${id}/record/`, payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', id] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.invalidateQueries({ queryKey: ['attendance-stats'] });
      queryClient.invalidateQueries({ queryKey: ['recent-sessions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
  });
}

/* ---- Live check-in ----
   Three distinct operations rather than one ambiguous toggle, matching
   the two genuinely different taps in the UI: tapping a row checks
   someone in or out, tapping "Mark online" changes only their mode
   without affecting whether they are present at all.

   Each call is its own request. That is deliberate: several ushers on
   different doors work the same session at once, and a batched
   "submit everything" form would let one overwrite another's taps. */

export function useCheckIn(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ memberId, mode }: { memberId: number; mode?: CheckInMode }) =>
      (await apiClient.post<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { member_id: memberId, mode: mode ?? 'in-person' },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session', sessionId] }),
  });
}

export function useCheckOut(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (memberId: number) =>
      (await apiClient.delete<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { data: { member_id: memberId } },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session', sessionId] }),
  });
}

export function useSetCheckInMode(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ memberId, mode }: { memberId: number; mode: CheckInMode }) =>
      (await apiClient.patch<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { member_id: memberId, mode },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session', sessionId] }),
  });
}

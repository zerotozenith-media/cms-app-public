import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type {
  MeetingType, AttendanceSession, AttendanceStats, RecordAttendancePayload,
  AttendanceSessionMember, CheckInMode, Fellowship,
} from '../types/attendance';

export function useMeetingTypes(opts: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ['meeting-types'],
    enabled: opts.enabled ?? true,
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
  /** Who the meeting was for: everyone, workers or leadership. */
  audience?: string;
  date_from?: string;
  date_to?: string;
  /** "no" finds services where nobody was ticked off by name, which is
   *  exactly where absence follow-up silently did not happen. */
  checked_in?: string;
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
    mutationFn: async (payload: {
      meeting_type: string; date: string; location: string; mode: string;
      /** Only for a house fellowship, since several meet the same evening. */
      fellowship?: number;
    }) => {
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

/** Who a tap is for: a member, or a newcomer whose Friday attendance
 *  builds up towards membership. */
export type CheckInWho = { memberId: number } | { newcomerId: number };
const whoBody = (w: CheckInWho) => ('memberId' in w ? { member_id: w.memberId } : { newcomer_id: w.newcomerId });

export function useCheckIn(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ mode, ...who }: CheckInWho & { mode?: CheckInMode }) =>
      (await apiClient.post<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { ...whoBody(who as CheckInWho), mode: mode ?? 'in-person' },
      )).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] });
      qc.invalidateQueries({ queryKey: ['newcomer-roster', sessionId] });
    },
  });
}

export function useCheckOut(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (who: CheckInWho) =>
      (await apiClient.delete<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { data: whoBody(who) },
      )).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] });
      qc.invalidateQueries({ queryKey: ['newcomer-roster', sessionId] });
    },
  });
}

export function useSetCheckInMode(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ mode, ...who }: CheckInWho & { mode: CheckInMode }) =>
      (await apiClient.patch<{ attendees: AttendanceSessionMember[] }>(
        `/attendance-sessions/${sessionId}/check_in/`,
        { ...whoBody(who as CheckInWho), mode },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['session', sessionId] }),
  });
}

export interface RosterNewcomer {
  id: number;
  name: string;
  stage: string;
  /** On Friday Worship only: Fridays so far, as the membership rule counts them. */
  fridays_attended?: number;
  fridays_held?: number;
}

/** Newcomers who can be checked in to this session. */
export function useNewcomerRoster(sessionId: number, enabled = true) {
  return useQuery({
    queryKey: ['newcomer-roster', sessionId],
    enabled,
    queryFn: async () => (await apiClient.get<{ fridays: boolean; results: RosterNewcomer[] }>(
      `/attendance-sessions/${sessionId}/newcomer-roster/`)).data,
  });
}

/** The house fellowships. Configurable, because the number changes. */
export function useFellowships() {
  return useQuery({
    queryKey: ['fellowships'],
    queryFn: async () =>
      (await apiClient.get<PaginatedResponse<Fellowship>>('/fellowships/')).data.results,
  });
}

export function useCreateFellowship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; area?: string; location?: string | null }) =>
      (await apiClient.post('/fellowships/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fellowships'] }),
  });
}

export function useDeleteFellowship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => (await apiClient.delete(`/fellowships/${id}/`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fellowships'] }),
  });
}

/** The month's figures as a formatted spreadsheet, for whoever combines
 *  several locations and would otherwise retype them out of the PDF. */
export async function downloadMonthlySpreadsheet(year: number, month: number, location?: string) {
  const resp = await apiClient.get('/reports/spreadsheet/', {
    params: { year, month, ...(location ? { location } : {}) }, responseType: 'blob',
  });
  const url = URL.createObjectURL(resp.data as Blob);
  const a = document.createElement('a');
  a.href = url;
  // The server names the file after the figures it actually sent, which
  // for somebody limited to one location is theirs, whatever was asked.
  const disposition = String((resp.headers as Record<string, string>)['content-disposition'] ?? '');
  const named = /filename="?([^"]+)"?/.exec(disposition)?.[1];
  a.download = named || `DCLM-${location || 'all-locations'}-${year}-${String(month).padStart(2, '0')}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Changing one field on a meeting type: who it is for, or whether it
 *  collects an offering. Both are rules the church sets, not a developer. */
export function useUpdateMeetingType() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...patch }: { id: string } & Partial<MeetingType>) =>
      (await apiClient.patch<MeetingType>(`/meeting-types/${id}/`, patch)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meeting-types'] });
      qc.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

export interface AbsentPreview {
  /** Why nothing can be done yet, such as nobody ticked. */
  blocked?: string;
  to_follow_up: number;
  names: string[];
  ticked: string[];
  already: number;
  open_elsewhere: number;
  /** Whether the meeting follows up absence on its own (for 7 days). */
  tracked: boolean;
}

/** "Follow up those not ticked": who would get a task. Refreshed after every tap. */
export function useAbsentPreview(sessionId: number, ticks: number, enabled: boolean) {
  return useQuery({
    queryKey: ['absent-preview', sessionId, ticks],
    enabled,
    retry: false,
    queryFn: async () => (await apiClient.get<AbsentPreview>(`/attendance-sessions/${sessionId}/follow-up-absent/`)).data,
  });
}

export function useFollowUpAbsent(sessionId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await apiClient.post<{ created: number }>(`/attendance-sessions/${sessionId}/follow-up-absent/`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['absent-preview', sessionId] });
      qc.invalidateQueries({ queryKey: ['member-followup-tasks'] });
    },
  });
}

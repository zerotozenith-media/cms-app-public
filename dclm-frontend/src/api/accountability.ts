import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/**
 * Follow-up accountability (Kay, 26 October 2026): a shepherd's one list,
 * results, reasons for late tasks, the Follow-up Coordinator's Review list,
 * alerts kept in the app, and Away dates.
 */
export type PersonType = 'member' | 'newcomer';

export interface TaskRow {
  type: PersonType;
  id: number;
  person_id: number;
  person: string;
  person_kind: string;
  location: string;
  text: string;
  kind: string;
  kind_label: string;
  missed_meeting_name: string;
  missed_date: string | null;
  missed_in_row: number;
  due_at: string | null;
  due_date: string;
  is_late: boolean;
  needs_reason: boolean;
  on_review: boolean;
  decide_by: string | null;
  escalation: string;
  escalation_label: string;
  result_note: string;
  shepherd_id: number | null;
  shepherd: string;
  handed_from: string;
  attempts: { date: string; at: string; method: string; note: string }[];
  reason: { reason: string; note: string; new_date: string; given_at: string } | null;
  last_choice: { choice: string; note: string; at: string } | null;
  shepherd_late_this_quarter?: number;
}

export interface PersonGroup {
  type: PersonType;
  person_id: number;
  person: string;
  person_kind: string;
  tasks: TaskRow[];
  needs_reason: number;
  late: number;
  priority: boolean;
  run: number;
}

export interface AwayRow {
  type: PersonType;
  person_id?: number;
  id?: number;
  person: string;
  away_from: string | null;
  away_to: string;
  away_reason?: string;
  reason?: string;
  shepherd?: string;
}

export interface MyFollowUp {
  people: PersonGroup[];
  away: AwayRow[];
  needs_reason: number;
  open: number;
}

export interface FollowUpAccess {
  can_shepherd: boolean;
  has_tasks: boolean;
  can_review: boolean;
  is_coordinator: boolean;
  is_administrator: boolean;
  coverage: string | null;
  coverage_name: string;
  can_edit_members: boolean;
  can_edit_newcomers: boolean;
}

export const taskBase = (t: PersonType) => (t === 'member' ? '/member-followup-tasks' : '/newcomer-tasks');
export const personBase = (t: PersonType) => (t === 'member' ? '/members' : '/newcomers');

/** The server's own words for a refusal, so the person always knows why. */
export function refusal(e: any, fallback: string) {
  const d = e?.response?.data;
  if (!d) return fallback;
  if (typeof d === 'string') return fallback;
  if (d.detail) return String(d.detail);
  const first = Object.values(d)[0];
  return first ? String(([] as unknown[]).concat(first as any)[0]) : fallback;
}

export function useFollowUpAccess() {
  return useQuery({
    queryKey: ['followup-access'],
    queryFn: async () => (await apiClient.get<FollowUpAccess>('/followup/access/')).data,
    staleTime: 60_000,
  });
}

export function useMyFollowUp(shepherd?: number | null) {
  return useQuery({
    queryKey: ['followup-my', shepherd ?? null],
    queryFn: async () => (await apiClient.get<MyFollowUp>('/followup/my/', { params: shepherd ? { shepherd } : {} })).data,
    refetchInterval: 120_000,
  });
}

/** Every follow-up list that might show a changed task. */
function refreshAll(qc: ReturnType<typeof useQueryClient>) {
  ['followup-my', 'followup-review', 'followup-overview', 'followup-shepherd', 'member-followup-tasks',
    'member-followup-stats', 'newcomer-tasks', 'all-newcomer-tasks', 'notifications', 'members', 'newcomers',
    'newcomers-all', 'member', 'newcomer', 'person'].forEach((k) =>
    qc.invalidateQueries({ queryKey: [k] }));
}

export interface ResultPayload {
  result: 'reached' | 'tried' | 'known-reason' | 'needs-coordinator' | 'moved-away';
  contact_date?: string;
  contact_method?: string;
  contact_goal?: string;
  contact_scripture?: string;
  contact_root_cause?: string;
  contact_next_step?: string;
  next_step_date?: string | null;
  method?: string;
  note?: string;
  away_from?: string | null;
  away_to?: string | null;
  away_reason?: string;
}

export function useRecordResult() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id, payload }: { type: PersonType; id: number; payload: ResultPayload }) =>
      (await apiClient.post(`${taskBase(type)}/${id}/record-result/`, payload)).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useGiveReason() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id, reason, note, new_date }: { type: PersonType; id: number; reason: string; note: string; new_date: string }) =>
      (await apiClient.post(`${taskBase(type)}/${id}/give-reason/`, { reason, note, new_date })).data,
    onSuccess: () => refreshAll(qc),
  });
}

/** Every late task's reason at once: checked and saved together, one alert. */
export function useGiveReasons() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (items: { type: PersonType; id: number; reason: string; note: string; new_date: string }[]) =>
      (await apiClient.post('/followup/reasons/', { items })).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id, reason, note }: { type: PersonType; id: number; reason: string; note: string }) =>
      (await apiClient.post(`${taskBase(type)}/${id}/cancel/`, { reason, note })).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useChangeDue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id, due_at, why }: { type: PersonType; id: number; due_at: string; why: string }) =>
      (await apiClient.post(`${taskBase(type)}/${id}/change-due/`, { due_at, why })).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useSetAway() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ type, id, clear, ...body }: { type: PersonType; id: number; clear?: boolean; away_from?: string; away_to?: string; away_reason?: string; away_note?: string }) =>
      clear ? (await apiClient.delete(`${personBase(type)}/${id}/away/`)).data
        : (await apiClient.post(`${personBase(type)}/${id}/away/`, body)).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useReviewList(location: string | null) {
  return useQuery({
    queryKey: ['followup-review', location],
    queryFn: async () => (await apiClient.get<{ results: TaskRow[] }>('/followup/review/', { params: location ? { location } : {} })).data.results,
  });
}

export function useDecide() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { type: PersonType; id: number; choice: string; note?: string; handed_to?: number }) =>
      (await apiClient.post('/followup/review/decide/', body)).data,
    onSuccess: () => refreshAll(qc),
  });
}

export function useEligible(type: PersonType, id: number, enabled: boolean) {
  return useQuery({
    queryKey: ['followup-eligible', type, id],
    queryFn: async () => (await apiClient.get<{ results: { id: number; name: string }[]; why: string }>('/followup/review/eligible/', { params: { type, id } })).data,
    enabled,
  });
}

export interface Overview {
  month: string;
  location: string | null;
  stats: { open: number; review: number; late_no_reason: number; away: number; names_not_taken: number };
  measures: { on_time: number | null; first_contact_hours: number | null; reached: number | null; due: number; late_no_reason: number; run: number };
  targets: { on_time: number; first_contact_hours: number; reached: number; late_no_reason: number; run_at: number };
  shepherds: { id: number; name: string; people: number; limit: number; open: number; on_time: number | null; reached: number | null; late_no_reason: number }[];
  away: AwayRow[];
  names_not_taken: { id: number; name: string }[];
}

export function useReviewOverview(location: string | null, month: string) {
  return useQuery({
    queryKey: ['followup-overview', location, month],
    queryFn: async () => (await apiClient.get<Overview>('/followup/review/overview/', { params: { ...(location ? { location } : {}), month } })).data,
  });
}

export interface ShepherdPerson { type: PersonType; id: number; person: string; label: string; status: string; tone: string; open: number }

export function useShepherdPeople(id: number | null, location: string | null) {
  return useQuery({
    queryKey: ['followup-shepherd', id, location],
    queryFn: async () => (await apiClient.get<{ results: ShepherdPerson[] }>(`/followup/review/shepherd/${id}/`, { params: location ? { location } : {} })).data.results,
    enabled: !!id,
  });
}

export interface Notice { id: number; kind: string; title: string; body: string; url: string; created_at: string; read: boolean }

export function useNotices() {
  return useQuery({
    queryKey: ['notices'],
    queryFn: async () => (await apiClient.get<{ unread: number; results: Notice[] }>('/alerts/notices/')).data,
    refetchInterval: 120_000, staleTime: 60_000,
  });
}

export function useMarkNoticesRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ids?: number[]) => (await apiClient.post('/alerts/notices/', ids ? { ids } : {})).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notices'] }),
  });
}

/** The church's clock: every follow-up time is Bahrain time, whatever
 *  time zone a phone is set to, so 6:00 pm always reads 6:00 pm. */
export const CHURCH_TZ = 'Asia/Bahrain';

/** "Saturday 31 October, 6:00 pm" */
export function whenText(iso: string | null | undefined) {
  if (!iso) return '';
  const d = new Date(iso);
  const day = d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', timeZone: CHURCH_TZ });
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: CHURCH_TZ }).toLowerCase();
  return `${day}, ${time}`;
}

/** "Friday 30 October" from "2026-10-30" */
export function dayText(date: string | null | undefined) {
  if (!date) return '';
  const d = new Date(`${date}T12:00:00`);
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

export const REASONS: [string, string][] = [
  ['tried', 'Tried but could not reach'],
  ['person-away', 'Person travelling or sick'],
  ['i-was-away', 'I was away or unwell'],
  ['too-many', 'Too many people to follow up'],
  ['forgot', 'Forgot'],
  ['other', 'Other'],
];

export const ATTEMPT_METHODS = ['Phone call', 'WhatsApp', 'Text message', 'Social media message', 'Email', 'Home visit'];

export const AWAY_REASONS: [string, string][] = [
  ['travelling', 'Travelling'], ['sick', 'Sick'], ['shift-abroad', 'Working a shift abroad'], ['other', 'Other'],
];

export const CANCEL_REASONS: [string, string][] = [
  ['was-at-service', 'The person was at the service'],
  ['did-not-hold', 'The service did not hold'],
  ['left', 'The person has left the church'],
  ['other', 'Other'],
];

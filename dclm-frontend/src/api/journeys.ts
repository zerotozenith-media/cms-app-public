import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** Follow-up journeys (F19, F20). */
export type JourneyKey = 'online' | 'newcomers' | 'converts';
export interface Template { id: number; theme: string; verse: string; reference: string; body: string; final?: boolean }
export interface TodayEntry {
  enrolment: number; journey: JourneyKey; journey_label: string; day: number; plan: 'standard' | 'daily'; belonging: boolean;
  person: { name: string; first: string; phone: string; kind: 'newcomer' | 'member' | 'enquiry'; id: number };
  template: Template | null; next_service: string; follower: string;
  done: { kind: 'planned' | 'own' | 'reply' | 'skipped'; text: string } | null;
}
export interface BankRow extends Template { journey: JourneyKey | 'any'; number: number; active: boolean; plan_days: { journey: string; day: number }[] }
export interface PersonEnrolment {
  id: number; journey: JourneyKey; journey_label: string; status: 'active' | 'stopped' | 'ended' | 'moved'; started: string;
  plan: 'standard' | 'daily'; day: number; ended_reason: string; ended_on: string | null; belonging: boolean; visits: number | null;
  strip: { day: number; state: string }[]; log: { day: number; kind: string; theme: string; text: string; on_date: string; by: string }[];
  steps: { when: string; what: string; done: boolean }[]; can_act: boolean;
}

export function useToday() {
  return useQuery({ queryKey: ['followup-today'], queryFn: async () => (await apiClient.get<{ date: string; results: TodayEntry[] }>('/followup/today/')).data });
}
export function useBank() {
  return useQuery({ queryKey: ['followup-bank'], queryFn: async () => (await apiClient.get<{ results: BankRow[]; can_edit: boolean; groups: { key: string; label: string }[] }>('/followup/bank/')).data, staleTime: 300_000 });
}
export function useSaved() {
  return useQuery({ queryKey: ['followup-saved'], queryFn: async () => (await apiClient.get<{ results: { id: number; html: string }[] }>('/followup/saved/')).data });
}
export function usePersonFollowUp(kind: 'newcomer' | 'member' | 'enquiry', id: number) {
  return useQuery({ queryKey: ['followup-person', kind, id], enabled: !!id, retry: (n, e: any) => e?.response?.status !== 404 && n < 2,
    queryFn: async () => (await apiClient.get<{ enrolments: PersonEnrolment[] }>('/followup/person/', { params: { [kind]: id } })).data });
}
export function useFollowUpAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (v: { url: string; body?: object; method?: 'post' | 'patch' | 'delete' }) =>
      (await apiClient.request({ url: v.url, method: v.method ?? 'post', data: v.body ?? {} })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['followup-today'] }); qc.invalidateQueries({ queryKey: ['followup-person'] }); qc.invalidateQueries({ queryKey: ['followup-saved'] }); qc.invalidateQueries({ queryKey: ['notifications'] }); },
  });
}

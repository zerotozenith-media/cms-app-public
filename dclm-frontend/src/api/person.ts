import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface PersonEvent { date: string; kind: string; title: string; detail?: string; by?: string; method?: string }
export interface PersonSummary {
  first_came: string | null;
  how_came: string;
  newcomer_id: number | null;
  member_id: number | null;
  journey: PersonEvent[];
  milestones: { name: string; date: string | null }[];
  open_follow_ups: { kind: 'newcomer' | 'member'; id: number; text: string; due_date: string; by: string }[];
  attendance: { count: number; recent: { date: string; meeting: string; as: 'newcomer' | 'member' }[] };
}

/** One summary for either profile (F16), so both tell the same story. */
export function usePerson(kind: 'members' | 'newcomers', id: number) {
  return useQuery({
    queryKey: ['person', kind, id],
    queryFn: async () => (await apiClient.get<PersonSummary>(`/${kind}/${id}/person/`)).data,
    enabled: !!id,
  });
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** The service ladder (F21). */
export interface MyService {
  eligible: boolean; level: number; level_name: string; scripture: string; points: number;
  next_level_name: string | null; keeping: boolean; points_needed: number;
  steps: { count: number; text: string }[]; grace_until: string | null;
  note: { kind: 'moved_up' | 'notice'; text: string } | null;
  levels: { name: string; scripture: string; from: number }[];
}
export interface TeamRow { id: number; name: string; initials: string; level: number; level_name: string; points: number; is_me: boolean }

export function useMyService() {
  return useQuery({ queryKey: ['service-me'], queryFn: async () => (await apiClient.get<MyService>('/service/me/')).data, staleTime: 60_000 });
}
export function useTeam() {
  return useQuery({ queryKey: ['service-team'], queryFn: async () => (await apiClient.get<{ results: TeamRow[] }>('/service/team/')).data, staleTime: 60_000 });
}
export function useDismissNote() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: async () => (await apiClient.post('/service/me/dismiss/', {})).data, onSuccess: () => qc.invalidateQueries({ queryKey: ['service-me'] }) });
}

/** The hover note: "Labourer. 378 points in the last 90 days. 72 more to become a Soul Winner." */
export function standingNote(level: string, points: number, next: string | null, needed: number, keeping = false) {
  const article = (w: string) => (/^[AEIOU]/.test(w) ? 'an ' : 'a ') + w;
  const tail = keeping ? `${needed} more to keep ${level}.` : next ? `${needed} more to become ${article(next)}.` : 'The highest level.';
  return `${points} points in the last 90 days. ${tail}`;
}

// Names used by the service ladder screens.
export const useServiceMe = useMyService;
export const useServiceTeam = useTeam;
export const useDismissServiceNote = useDismissNote;

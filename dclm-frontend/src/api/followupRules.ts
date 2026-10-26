import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** Admin, Follow-up Rules (Kay, 26 October 2026). Every follow-up time and
 *  number, one set for every location. */
export interface FollowUpRules {
  clock_start: string;
  due_hours: number;
  reason_hours: number;
  review_days: number;
  decide_days: number;
  max_new_date_days: number;
  alert_from_miss: number;
  alert_repeat: 'every' | 'every-second';
  visit_task_at_miss: number;
  attempts_before_coordinator: number;
  falling_percent: number;
  falling_window: number;
  shepherd_limit: number;
  newcomer_stages: string[];
  check_hours_after_start: number;
  remind_administrators: boolean;
  remind_location_coordinators: boolean;
  morning_alert_time: string;
  target_on_time: number;
  target_first_contact_hours: number;
  target_reached: number;
  updated_at: string | null;
  updated_by_name: string;
  can_change: boolean;
}

export function useFollowUpRules() {
  return useQuery({
    queryKey: ['followup-rules'],
    queryFn: async () => (await apiClient.get<FollowUpRules>('/followup-rules/')).data,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSaveFollowUpRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<FollowUpRules>) => (await apiClient.patch<FollowUpRules>('/followup-rules/', patch)).data,
    onSuccess: (data) => qc.setQueryData(['followup-rules'], data),
  });
}

export function useResetFollowUpRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await apiClient.post<FollowUpRules>('/followup-rules/', {})).data,
    onSuccess: (data) => qc.setQueryData(['followup-rules'], data),
  });
}

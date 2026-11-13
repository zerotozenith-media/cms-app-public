import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

/** Admin, Follow-up Rules (26 October 2026). Every follow-up time and
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
  /** All-locations accounts can shepherd at any location (5 November 2026). */
  shepherd_anywhere: boolean;
  newcomer_stages: string[];
  /** Fewer tasks (13 November 2026). */
  one_open_task: boolean;
  lapsed_after_misses: number;
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
    onSuccess: (data) => {
      qc.setQueryData(['followup-rules'], data);
      // Who can shepherd where follows the rules.
      qc.invalidateQueries({ queryKey: ['eligible-shepherds'] });
      qc.invalidateQueries({ queryKey: ['shepherds-not-offered'] });
    },
  });
}

export function useResetFollowUpRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await apiClient.post<FollowUpRules>('/followup-rules/', {})).data,
    onSuccess: (data) => {
      qc.setQueryData(['followup-rules'], data);
      // Who can shepherd where follows the rules.
      qc.invalidateQueries({ queryKey: ['eligible-shepherds'] });
      qc.invalidateQueries({ queryKey: ['shepherds-not-offered'] });
    },
  });
}

export interface CleanupResult { tasks_joined: number; people_with_extra_tasks: number; lapsed: number; lapsed_names: string[] }

/** The one-off cleanup (13 November 2026): check first, then run. */
export function useCleanupPreview(enabled: boolean) {
  return useQuery({
    queryKey: ['followup-cleanup'],
    queryFn: async () => (await apiClient.get<CleanupResult>('/followup/cleanup/')).data,
    enabled,
    staleTime: 0,
  });
}

export function useRunCleanup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await apiClient.post<CleanupResult>('/followup/cleanup/')).data,
    onSuccess: () => {
      ['followup-cleanup', 'followup-lapsed', 'followup-review', 'my-followup', 'outstanding'].forEach((k) =>
        qc.invalidateQueries({ queryKey: [k] }));
    },
  });
}

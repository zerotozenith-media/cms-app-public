export type NewcomerStage = 'new' | 'contacted' | 'visiting' | 'integrated' | 'not-interested';

export interface MilestoneStatus {
  milestone_type_id: number;
  name: string;
  achieved_date: string | null;
}

export interface Newcomer {
  id: number;
  name: string;
  source: number;
  source_name: string;
  stage: NewcomerStage;
  assigned_to: number | null;
  assigned_to_name: string | null;
  location: string;
  created_at: string;
  stage_since: string;
  not_interested_note: string;
  days_in_stage: number;
  urgency: 'green' | 'amber' | 'red';
  milestones: MilestoneStatus[];
  open_tasks_count: number;
  address: string;
  city_governorate: string;
  phone: string;
  email: string;
  gender: string;
  age_group: string;
  prayer_request: string;
  meeting_attended: string | null;
  meeting_attended_name: string | null;
  is_first_timer: boolean;
  is_new_resident: boolean;
  wants_visit: boolean;
  wants_to_know_more: boolean;
  wants_salvation_info: boolean;
  invited_by_member: number | null;
  invited_by_member_name: string | null;
  invited_by_name: string;
}

export interface NewcomerTask {
  id: number;
  newcomer: number;
  text: string;
  due_date: string;
  /** Read-only from the API. Set only via the complete endpoint, which
   *  requires the four outcome fields below. */
  done: boolean;
  assigned_to: number | null;
  contact_date: string | null;
  contact_method: string;
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
  /** Legacy single-note field from before the structured fields. */
  contact_notes: string;
}

export interface NewcomerSource {
  id: number;
  name: string;
}

export interface MilestoneType {
  id: number;
  name: string;
}

export interface MemberCategoryHistoryEntry {
  id: number;
  member: number;
  from_category: string;
  to_category: string;
  changed_date: string;
}

export type MemberCategory = 'General Member' | 'Worker in Training' | 'Worker';

export interface Member {
  id: number;
  surname: string;
  first_name: string;
  other_names: string;
  full_name: string;
  gender: string;
  date_of_birth: string | null;
  phone: string;
  email: string;
  category: MemberCategory;
  location: string;
  joined_date: string;
  household: number | null;
  household_name: string | null;
  category_history: MemberCategoryHistoryEntry[];
  total_given: number;
  /** The worker responsible for this member's pastoral follow-up. Null
   *  means unassigned: a task is still created, it just has nobody
   *  attached and shows in the Unassigned count. */
  assigned_to: number | null;
  assigned_to_name: string | null;
}

export interface Household {
  id: number;
  name: string;
  address: string;
  phone: string;
  member_count: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface MemberListParams {
  search?: string;
  category?: string;
  ordering?: string;
  page?: number;
}


export type ContactMethod =
  | 'Home visit'
  | 'Phone call'
  | 'Text message'
  | 'Spoke after service'
  | 'Other';

export const CONTACT_METHODS: ContactMethod[] = [
  'Home visit', 'Phone call', 'Text message', 'Spoke after service', 'Other',
];

export interface MemberFollowUpTask {
  id: number;
  member: number;
  member_name: string;
  text: string;
  due_date: string;
  done: boolean;
  assigned_to: number | null;
  assigned_to_name: string | null;
  /** A durable snapshot of what triggered this, kept as text so the task
   *  still reads correctly even if the session is later deleted. */
  missed_session: number | null;
  missed_meeting_name: string;
  missed_date: string;
  contact_date: string | null;
  contact_method: ContactMethod | '';
  /** The four structured outcome fields. All required when completing,
   *  because a ticked box with no record is not useful months later. */
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
  /** Legacy single-note field, kept so records created before the four
   *  structured fields existed still display. */
  contact_notes: string;
}

export interface CompleteFollowUpPayload {
  contact_date?: string;
  contact_method: ContactMethod;
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
}

export interface FollowUpStats {
  open_followups: number;
  overdue: number;
  unassigned: number;
}

/** One proposed change from the assignment preview. Nothing is saved
 *  until these are posted back to the apply endpoint. */
export interface AssignmentChange {
  kind: 'member' | 'newcomer';
  id: number;
  name: string;
  from_name: string | null;
  to_id: number;
  to_name: string;
  reason: 'Household' | 'Balanced load';
}

export interface AssignmentPreview {
  reassign_everyone: boolean;
  count: number;
  changes: AssignmentChange[];
}

export interface AssignmentApplyResult {
  applied_members: number;
  applied_newcomers: number;
  changes: AssignmentChange[];
}

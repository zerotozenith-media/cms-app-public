export interface MemberCategoryHistoryEntry {
  id: number;
  member: number;
  from_category: string;
  to_category: string;
  changed_date: string;
}

export type MemberCategory = 'General Member' | 'Worker in Training' | 'Worker';

export interface Member {
  /** How they came to the church, where known. */
  arrived_via?: string;
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
  /** Expected at leadership meetings. Independent of category, because a
   *  leader is a Worker who also leads. */
  is_leader: boolean;
  from_newcomer: number | null;
  household: number | null;
  household_name: string | null;
  category_history: MemberCategoryHistoryEntry[];
  total_given: number;
  /** The worker responsible for this member's pastoral follow-up. Null
   *  means unassigned: a task is still created, it just has nobody
   *  attached and shows in the Unassigned count. */
  assigned_to: number | null;
  assigned_to_name: string | null;
  /** What is wrong with their shepherd, such as "A man shepherds her",
   *  or empty when the pairing keeps the rules. */
  shepherd_problem?: string;
}

/** Members whose shepherd breaks a rule, for the box at the top of Members. */
export interface ShepherdProblems {
  count: number;
  people: { id: number; name: string; tag: string }[];
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
  from_pipeline?: string;
  search?: string;
  category?: string;
  /** A user id, or "none" to find members with nobody assigned. */
  shepherd?: string;
  /** A household id, or "none" for members not linked to one. */
  household?: string;
  is_leader?: string;
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
  /** Blank for a task added by hand, which is not about a missed service. */
  missed_meeting_name: string;
  missed_date: string | null;
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
  gender?: string;
  from_id?: number | null;
  from_name: string | null;
  /** A shepherd who breaks a rule is being replaced, not a gap filled. */
  correction?: boolean;
  /** Shepherds never offered for this person: themselves, and one being replaced. */
  never?: number[];
  /** null when nobody suitable exists, shown so the reviewer sees why. */
  to_id: number | null;
  to_name: string | null;
  reason: string;
  /** Check before applying, such as gender not known. */
  warn?: boolean;
}

/** Each shepherd's load now and after the proposed changes. Without it a
 *  batch that goes to one worker reads as a fault, when that worker was
 *  simply carrying far fewer than the rest. */
export interface ShepherdLoad {
  id: number;
  name: string;
  gender?: string;
  now: number;
  after: number;
}

export interface AssignmentPreview {
  reassign_everyone: boolean;
  count: number;
  load?: ShepherdLoad[];
  changes: AssignmentChange[];
  /** Shepherds with no gender set, whom auto-assign gives nobody. */
  notice?: string;
}

export interface AssignmentApplyResult {
  applied_members: number;
  applied_newcomers: number;
  changes: AssignmentChange[];
}

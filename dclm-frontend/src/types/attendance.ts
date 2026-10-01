export type MeetingAudience = 'everyone' | 'workers' | 'leadership';

export const AUDIENCES: { key: MeetingAudience; label: string; note: string }[] = [
  { key: 'everyone', label: 'Everyone', note: 'All members are expected' },
  { key: 'workers', label: 'Workers', note: 'Workers only, not Workers in Training' },
  { key: 'leadership', label: 'Leadership', note: 'Members ticked as a leader' },
];

export interface Fellowship {
  id: number;
  name: string;
  area: string;
  /** Where it meets. Null means every location. */
  location: string | null;
  location_name: string;
  meeting_type: string | null;
  is_active: boolean;
  session_count: number;
}

export interface MeetingType {
  /** Who is expected, and so who is followed up when absent. */
  audience: MeetingAudience;
  /** Whether the session form asks for an offering. Set in Admin rather
   *  than fixed in code, so the church can change it. */
  collects_offering: boolean;
  /** False when the day is not a weekday the generator recognises, in
   *  which case no sessions are being created for this meeting. */
  generates_sessions: boolean;
  /** The one target every screen shows: the goal where set, otherwise the
   *  meeting's own figure. */
  effective_target: number | null;
  id: string;
  name: string;
  day: string;
  frequency: 'weekly' | 'occasional';
  detail_level: 'detailed' | 'simple';
  monthly_target: number | null;
  /** When true, anyone not checked in to this meeting is treated as
   *  absent a few hours after it starts and a follow-up task is created
   *  for their shepherd. Off by default. */
  counts_for_absence: boolean;
  /** Local wall-clock start time, e.g. "18:00:00". Needed so the absence
   *  check knows when the service actually began. Null means this meeting
   *  is never auto-checked, whatever counts_for_absence says. */
  start_time: string | null;
}

export type CheckInMode = 'in-person' | 'online';

export interface AttendanceSessionMember {
  id: number;
  member: number;
  member_name: string;
  /** Per attendee, not per session, so one hybrid service can have some
   *  people in person and others online. */
  mode: CheckInMode;
  checked_in_at: string;
}

export interface AttendanceSession {
  /** Online attendance, counted separately. Any meeting can be hybrid,
   *  and a total showing only the room understates the month. */
  online_men: number;
  online_women: number;
  online_youth_boys: number;
  online_youth_girls: number;
  online_children_boys: number;
  online_children_girls: number;
  online_total: number;
  in_person_total: number;
  /** How many were new tonight, which is a different question from who. */
  new_comers: number;
  new_converts: number;
  /** Only used when the meeting is a house fellowship. */
  fellowship: number | null;
  fellowship_name: string | null;
  led_by: number | null;
  led_by_name: string | null;
  lesson: string;
  // F22: an occasional meeting's edition.
  edition_name: string;
  edition_place: string;
  id: number;
  meeting_type: string;
  meeting_type_name: string;
  date: string;
  location: string;
  mode: 'in-person' | 'online';
  status: 'pending' | 'filled';
  track_named: boolean;
  men: number;
  women: number;
  youth_boys: number;
  youth_girls: number;
  children_boys: number;
  children_girls: number;
  total: number;
  attendees: AttendanceSessionMember[];
}

export interface AttendanceStats {
  sessions_this_month: number;
  filled: number;
  pending: number;
}

export interface RecordAttendancePayload {
  online_men?: number;
  online_women?: number;
  online_youth_boys?: number;
  online_youth_girls?: number;
  online_children_boys?: number;
  online_children_girls?: number;
  new_comers?: number;
  new_converts?: number;
  led_by?: number | null;
  lesson?: string;
  edition_name?: string;
  edition_place?: string;
  men: number;
  women: number;
  youth_boys: number;
  youth_girls: number;
  children_boys: number;
  children_girls: number;
  track_named: boolean;
  attendee_ids: number[];
}

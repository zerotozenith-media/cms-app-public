export interface MeetingType {
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
  men: number;
  women: number;
  youth_boys: number;
  youth_girls: number;
  children_boys: number;
  children_girls: number;
  track_named: boolean;
  attendee_ids: number[];
}

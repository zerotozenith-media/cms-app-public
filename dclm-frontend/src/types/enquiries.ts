/**
 * Online enquiries: people who contacted the church through social
 * media or the website and left a way to reach them, but have not
 * attended a service.
 *
 * Deliberately separate from Newcomer. A newcomer came to a meeting; an
 * enquirer has not, may live anywhere, and the immediate goal is to make
 * contact and invite them rather than integrate them.
 */

export type EnquiryStage = 'new' | 'contacted' | 'invited' | 'attended' | 'not-pursuing';

export const ENQUIRY_STAGES: { key: EnquiryStage; label: string }[] = [
  { key: 'new', label: 'New' },
  { key: 'contacted', label: 'Contacted' },
  { key: 'invited', label: 'Invited' },
  { key: 'attended', label: 'Attended' },
];

export interface EnquirySource {
  id: number;
  name: string;
}

export interface Enquiry {
  id: number;
  name: string;
  source: number;
  source_name: string;
  phone: string;
  email: string;
  social_handle: string;
  /** Whichever contact we actually have, most direct first. */
  best_contact: string;
  enquiry_text: string;
  /** Free text, not a church location: an enquirer may be outside Bahrain. */
  area: string;
  stage: EnquiryStage;
  stage_since: string;
  received_at: string;
  assigned_to: number | null;
  assigned_to_name: string | null;
  not_pursuing_note: string;
  converted_newcomer: number | null;
  converted_newcomer_name: string | null;
  open_tasks_count: number;
  days_in_stage: number;
}

export interface EnquiryTask {
  id: number;
  enquiry: number;
  enquiry_name: string;
  text: string;
  due_date: string;
  /** Read-only from the API; set only through the complete endpoint. */
  done: boolean;
  assigned_to: number | null;
  assigned_to_name: string | null;
  contact_date: string | null;
  contact_method: string;
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
}

export const ENQUIRY_CONTACT_METHODS = [
  'Phone call', 'WhatsApp', 'Social media message', 'Email', 'Home visit', 'Other',
] as const;

export interface EnquiryStats {
  active: number;
  awaiting_first_contact: number;
  unassigned: number;
  overdue_tasks: number;
  converted: number;
}

export interface FollowUpDue {
  newcomer_id: number;
  newcomer_name: string;
  due_date: string;
  text: string;
}

export interface ShortTermGoal {
  id: number;
  name: string;
  current: number;
  target: number;
  unit: string;
  pct: number;
  link_route: string;
  link_tab: string;
}

/**
 * Phase 4.3 security fix: each section is now gated by the viewer's
 * real per-module permission and entirely omitted (not just empty) when
 * they lack it , a Members-only user's response genuinely has no
 * giving_total key at all, not a zero one. Every section's fields are
 * therefore optional here, present only alongside its own *_access: true.
 */
export interface DashboardSummary {
  attendance_access: boolean;
  friday_worship?: {
    total: number;
    target: number | null;
    trend: { date: string; total: number }[];
  };

  finance_access: boolean;
  giving_total?: number;
  expense_total?: number;
  net_total?: number;
  giving_by_fund?: { fund: string; value: number }[];
  fund_count?: number;

  newcomers_access: boolean;
  newcomers_in_pipeline?: number;
  pending_followups_count?: number;
  follow_ups_due?: FollowUpDue[];

  goals_access: boolean;
  short_term_goals?: ShortTermGoal[];
}

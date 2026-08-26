export type GoalHorizon = 'Short-term' | 'Medium-term' | 'Long-term' | 'Spiritual growth';

export interface Goal {
  id: number;
  horizon: GoalHorizon;
  name: string;
  target: number;
  current: number;
  unit: string;
  tracking: 'auto' | 'manual';
  period_type: string;
  source: string;
  link_route: string;
  link_tab: string;
  current_value: number;
  calculation_error: string | null;
}

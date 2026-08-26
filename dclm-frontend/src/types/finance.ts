export interface Fund { id: number; name: string; }
export interface PaymentMethod { id: number; name: string; }
export interface ExpenseCategory { id: number; name: string; }

export interface Project {
  id: string;
  name: string;
  description: string;
  location: string;
  target_amount: number;
  target_date: string | null;
  status: 'Active' | 'Completed' | 'Archived';
  amount_raised: number;
  amount_spent: number;
}

export interface Giving {
  id: number;
  date: string;
  fund: number;
  fund_name: string;
  method: number;
  method_name: string;
  amount: number;
  location: string;
  project: string | null;
  project_name: string | null;
  member: number | null;
  member_name: string | null;
}

export interface Expense {
  id: number;
  date: string;
  category: number;
  category_name: string;
  amount: number;
  location: string;
  description: string;
  receipt_file: string | null;
  project: string | null;
  project_name: string | null;
}

export interface FinanceSummary {
  income_total: number;
  income_this_month: number;
  expense_total: number;
  net_total: number;
  income_by_fund: { fund: string; total: number }[];
  expenses_by_category: { category: string; total: number }[];
}

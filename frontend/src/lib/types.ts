// Shapes returned by the backend API. Amounts are integer minor units (e.g. paise).

export interface Category { id: string; name: string; custom: boolean }
export interface PaymentMethod { id: string; name: string }
export interface Currency { code: string; symbol: string; exponent: number }

export interface Preferences {
  display_name: string | null
  currency: string
  timezone: string
  budget_thresholds: number[]
  anomaly_sensitivity: 'conservative' | 'balanced' | 'sensitive'
  custom_categories: { id: string; name: string }[]
  categories: Category[]
  updated_at: string
}

export interface Me {
  user: { id: string; email: string; name: string }
  preferences: Preferences
  auth_mode: 'local' | 'cognito'
  demo_data_enabled: boolean
}

export interface Reference { categories: Category[]; payment_methods: PaymentMethod[]; currencies: Currency[] }

export interface Expense {
  id: string
  amount_minor: number
  date: string
  category: string
  description: string
  merchant: string | null
  payment_method: string
  notes: string | null
  receipt_id: string | null
  is_demo: boolean
  created_at: string
  updated_at: string
}

export interface ExpensePage {
  items: Expense[]
  total_count: number
  total_amount_minor: number
  page: number
  page_size: number
  total_pages: number
}

export interface BudgetAlert { category_name: string; threshold: number; spent_minor: number; budget_minor: number }

export interface ExpenseMutation { expense: Expense; new_anomalies: number; budget_alerts: BudgetAlert[] }

export interface BudgetRow {
  budget_id: string
  category: string | null
  category_name: string
  effective_from: string
  amount_minor: number
  spent_minor: number
  remaining_minor: number
  utilization_pct: number | null
  status: 'ok' | 'warning' | 'at_limit' | 'exceeded'
  thresholds_crossed: number[]
  projected_spend_minor: number | null
  projected_overrun: boolean
  days_elapsed: number
  days_in_month: number
  daily_allowance_minor: number | null
}

export interface BudgetOverview {
  month: string
  total_spent_minor: number
  overall: BudgetRow | null
  categories: BudgetRow[]
  unbudgeted: { category: string; category_name: string; spent_minor: number }[]
  thresholds: number[]
  new_alerts: BudgetAlert[]
  alert_events: (BudgetAlert & { budget_key: string; created_at: string })[]
}

export interface BudgetHistoryRow {
  month: string
  spent_minor: number
  overall_budget_minor: number | null
  category_budget_total_minor: number | null
  utilization_pct: number | null
  within_budget: boolean | null
  categories_over_budget: string[]
  is_current: boolean
}

export interface InsightTxn { id: string; date: string; description: string; amount_minor: number; category: string }

export interface Insight {
  id: string
  kind: 'fact' | 'estimate' | 'projection' | 'recommendation' | 'data_gap'
  severity: 'critical' | 'warning' | 'info' | 'positive'
  title: string
  message: string
  category: string | null
  action: { label: string; href: string } | null
  evidence: {
    period: { start: string; end: string; label: string } | null
    calculation: string | null
    values: Record<string, unknown>
    transactions: InsightTxn[]
  }
}

export interface RecurringSeries {
  key: string
  name: string
  category: string
  cadence: 'weekly' | 'monthly'
  typical_amount_minor: number
  monthly_equivalent_minor: number
  occurrences: number
  confidence: 'high' | 'low'
  first_date: string
  last_date: string
  next_expected: string
  active: boolean
}

export interface InsightsResponse {
  month: string
  generated_for: { start: string; end: string; label: string }
  coverage: { months_with_data: number; first_month: string | null; transactions_in_period: number }
  recurring: RecurringSeries[]
  insights: Insight[]
}

export interface MonthSummary {
  month: string
  is_current_month: boolean
  period_start: string
  period_end: string
  total_minor: number
  transaction_count: number
  days_elapsed: number
  average_daily_minor: number
  previous_month: string
  previous_month_total_minor: number
  previous_comparable_total_minor: number
  comparison_period: { start: string; end: string; label: string }
  change_pct: number | null
  largest_expense: { id: string; description: string; amount_minor: number; date: string; category: string } | null
}

export interface CategoryRow { category: string; category_name: string; amount_minor: number; share_pct: number | null; count: number }
export interface MonthlyPoint { month: string; label: string; total_minor: number; by_category: Record<string, number> }
export interface DailyPoint { date: string; amount_minor: number }

export interface AnomalyExpense {
  id: string; description: string; merchant: string | null; amount_minor: number; date: string
  category: string; category_name: string; payment_method: string
}

export interface AnomalyAlert {
  id: string
  expense_id: string
  rule: 'category_outlier' | 'overall_outlier' | 'duplicate' | 'repeated_similar' | 'category_spike'
  severity: 'low' | 'medium' | 'high'
  reason: string
  comparison: Record<string, unknown>
  detected_at: string
  status: 'open' | 'reviewed' | 'legitimate' | 'dismissed'
  status_updated_at: string | null
  note: string | null
  is_demo: boolean
  expense: AnomalyExpense | null
}

export interface GoalContribution { id: string; amount_minor: number; date: string; note: string | null; kind: 'contribution' | 'starting_balance'; created_at: string }

export interface Goal {
  id: string
  name: string
  target_minor: number
  saved_minor: number
  target_date: string | null
  archived: boolean
  contributions: GoalContribution[]
  is_demo: boolean
  created_at: string
  updated_at: string
  remaining_minor: number
  progress_pct: number
  status: 'on_track' | 'behind' | 'not_started' | 'completed' | 'overdue' | 'archived'
  completed: boolean
  months_left: number | null
  required_monthly_minor: number | null
  recent_monthly_contribution_minor: number
  projected_completion_date: string | null
}

export interface Dashboard {
  month: string
  currency: string
  summary: MonthSummary
  budget: BudgetOverview
  categories: CategoryRow[]
  daily: DailyPoint[]
  monthly: MonthlyPoint[]
  recent_transactions: Expense[]
  insights: Insight[]
  anomalies: { open_count: number; items: AnomalyAlert[] }
  goals: Goal[]
  upcoming_targets: Goal[]
  category_names: Record<string, string>
}

export interface RangeAnalytics {
  start: string
  end: string
  days: number
  total_minor: number
  transaction_count: number
  average_daily_minor: number
  average_transaction_minor: number
  categories: CategoryRow[]
  payment_methods: { payment_method: string; name: string; amount_minor: number; share_pct: number | null; count: number }[]
  daily: DailyPoint[]
  monthly: MonthlyPoint[]
  top_merchants: { merchant: string; amount_minor: number; count: number }[]
  category_names: Record<string, string>
}

export interface ExtractedField<T = string | null> { value: T; confidence: number; source: string | null; verified_by?: string }

export interface Receipt {
  id: string
  content_type: string
  size_bytes: number
  status: 'pending_upload' | 'uploaded' | 'processed' | 'failed' | 'confirmed'
  error: string | null
  expense_id: string | null
  uploaded_at: string
  processed_at: string | null
  image_url: string
  extracted: null | {
    merchant: ExtractedField
    date: ExtractedField
    total: ExtractedField
    subtotal: string | null
    tax: ExtractedField & { components: { label: string; value: string }[] }
    currency: ExtractedField
    line_items: { description: string; quantity: number | null; amount: string; confidence: number }[]
    total_candidates: { value: string; source: string }[]
    suggested_category: ExtractedField
    warnings: string[]
    raw_text: string
    ocr_confidence: number
    line_count: number
    total_minor: number | null
    tax_minor: number | null
    currency_mismatch: boolean
  }
}

export interface SimulationRow {
  category: string; category_name: string; mode: string; value: string
  current_minor: number; new_minor: number; monthly_savings_minor: number
}

export interface SimulationScenarioResult {
  name: string
  rows: SimulationRow[]
  current_total_minor: number
  new_total_minor: number
  monthly_savings_minor: number
  annual_savings_minor: number
  warnings: string[]
  explanation: string
  budget?: { budget_minor: number; remaining_current_minor: number; remaining_new_minor: number }
  goal?: {
    goal_id: string; name: string; remaining_minor: number; required_monthly_minor: number | null
    current_monthly_contribution_minor: number; monthly_with_savings_minor: number
    months_to_goal: number | null; estimated_completion: string | null; meets_target_date: boolean; assumption: string
  }
}

export interface SimulationResponse {
  baseline: { mode: string; label: string; start: string; end: string; months: number; total_minor: number;
    is_projection?: boolean; categories: { category: string; category_name: string; amount_minor: number }[] }
  scenarios: SimulationScenarioResult[]
  best_scenario: string | null
  disclaimer: string
}

export interface AssistantReply {
  answer: string
  intent: string
  period: { start: string; end: string; label: string } | null
  data: Record<string, any> | null
  suggestions: string[]
  needs_clarification: boolean
  disclaimer: string
}

export interface Subscriber {
  id: number;
  subscription_number: string;
  phone_number: string;
  name: string;
  language: string;
  tariff_category: string;
  governorate: string;
  area: string;
  household_size: number | null;
  has_ev: boolean;
  has_solar: boolean;
  home_size_sqm: number | null;
}

export interface User {
  id: number;
  username: string;
  is_staff: boolean;
  subscriber: Subscriber | null;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface ConsumptionSummary {
  period_days: number;
  total_kwh: number;
  avg_daily_kwh: number;
  avg_daily_cost_fils: number;
  peak_share_percent: number;
  off_peak_share_percent: number;
  partial_peak_share_percent: number;
  highest_day: { date: string; kwh: number } | null;
  lowest_day: { date: string; kwh: number } | null;
  trend: "increasing" | "decreasing" | "stable";
  trend_percent_per_week: number;
}

export interface DailySeriesItem {
  date: string;
  total_kwh: number;
  peak_kwh: number;
  off_peak_kwh: number;
  partial_peak_kwh: number;
}

export interface SpikeEvent {
  timestamp: string;
  power_kw: number;
  baseline_kw: number;
  spike_factor: number;
  tou_period: string;
  duration_minutes: number;
  estimated_extra_cost_fils: number;
}

export interface SpikesResponse {
  spikes: SpikeEvent[];
  count: number;
}

export interface BillForecast {
  days_elapsed: number;
  days_remaining: number;
  actual_kwh_so_far: number;
  projected_monthly_kwh: number;
  projected_bill: {
    total_fils: number;
    total_jod: number;
    tier_reached: number;
    warning?: string;
  };
  last_month_kwh: number;
  last_month_bill_fils: number;
  change_vs_last_month_percent: number;
}

export interface HourlyProfile {
  period: { start: string; end: string };
  hourly_avg_kw: number[];
  peak_hour: number;
  peak_avg_kw: number;
  lowest_hour: number;
  lowest_avg_kw: number;
}

export interface TouPeriod {
  period: string;
  period_name_ar: string;
  period_name_en: string;
  start_time: string;
  end_time: string;
  minutes_remaining: number;
  next_period: string;
}

export interface AdminStats {
  total_subscribers: number;
  verified_subscribers: number;
  total_readings_30d: number;
  active_plans: number;
  total_plans: number;
}

export interface AdminSubscriber {
  id: number;
  subscription_number: string;
  name: string;
  phone_number: string;
  tariff_category: string;
  governorate: string;
  area: string;
  has_ev: boolean;
  has_solar: boolean;
  is_verified: boolean;
  last_reading_at: string | null;
  created_at: string;
}

export interface OptimizationPlan {
  id: number;
  plan_summary: string;
  detected_pattern: string;
  user_hypothesis: string;
  plan_details: Record<string, unknown>;
  baseline_daily_kwh: number;
  baseline_peak_kwh: number;
  status: string;
  verify_after_date: string | null;
  verification_result: Record<string, unknown> | null;
  created_at: string;
}

export interface TariffCalculation {
  total_fils: number;
  total_jod: number;
  fixed_charge_fils: number;
  energy_charge_fils: number;
  tier_breakdown: Array<{
    tier: number;
    kwh: number;
    rate_fils: number;
    cost_fils: number;
  }>;
  avg_rate_fils: number;
  monthly_kwh: number;
}

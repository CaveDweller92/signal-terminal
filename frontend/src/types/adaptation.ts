export interface ParameterSnapshot {
  id: number;
  snapshot_type: string;
  trigger: string | null;

  // Entry parameters
  rsi_period: number;
  rsi_overbought: number;
  rsi_oversold: number;
  ema_fast: number;
  ema_slow: number;
  volume_multiplier: number;
  min_signal_strength: number;
  technical_weight: number;
  sentiment_weight: number;
  fundamental_weight: number;

  // Exit parameters
  atr_stop_multiplier: number;
  atr_target_multiplier: number;
  default_stop_loss_pct: number;
  default_profit_target_pct: number;
  max_hold_bars: number;

  full_config: Record<string, unknown> | null;
  created_at: string;
}

export interface MetaReview {
  id: number;
  review_date: string;
  regime_at_review: string | null;
  summary: string;
  recommendations: string[] | Record<string, unknown> | null;
  parameter_adjustments: string[] | Record<string, unknown> | null;
  exit_strategy_assessment: string[] | Record<string, unknown> | null;
  signals_generated: number;
  signals_correct: number;
  avg_return: number | null;
  regime_accuracy: number | null;
  created_at: string;
}

export interface DailyPerformance {
  id: number;
  perf_date: string;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  signals_correct: number;
  signals_incorrect: number;
  win_rate: number | null;
  avg_return_pct: number | null;
  best_return_pct: number | null;
  worst_return_pct: number | null;
  total_return_pct: number | null;
  regime: string | null;
  breakdown: Record<string, unknown> | null;
  created_at: string;
}

export interface PerformanceSummary {
  days: number;
  total_signals: number;
  total_correct: number;
  overall_win_rate: number | null;
  avg_daily_return_pct: number | null;
  cumulative_return_pct: number | null;
  best_day: DailyPerformance | null;
  worst_day: DailyPerformance | null;
  daily: DailyPerformance[];
}

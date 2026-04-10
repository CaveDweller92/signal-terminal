export interface PriceBar {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export interface Indicators {
  rsi: number;
  macd_histogram: number;
  ema_crossover: string;
  ema_just_crossed: boolean;
  volume_ratio: number;
  atr: number;
  bollinger_pct_b?: number;
  stochastic_k?: number;
  stochastic_d?: number;
  adx?: number;
  divergence?: { type: string; confidence: number };
}

export interface SignalReasons {
  technical: string[];
  sentiment: string[];
  fundamental: string[];
}

export interface PositionSizing {
  shares: number;
  position_value: number;
  risk_amount: number;
  risk_pct_of_portfolio: number;
  conviction_multiplier: number;
  capped_at_max_position: boolean;
}

export interface Signal {
  id?: number;
  symbol: string;
  signal_type: 'BUY' | 'SELL' | 'HOLD';
  conviction: number;
  tech_score: number;
  sentiment_score: number;
  fundamental_score: number;
  price_at_signal: number;
  suggested_stop_loss: number;
  suggested_profit_target: number;
  atr_at_signal: number;
  regime_at_signal?: string;
  reasons: SignalReasons;
  indicators: Indicators;
  position_sizing?: PositionSizing;
}

export interface SignalListResponse {
  signals: Signal[];
  count: number;
  cached?: boolean;
  fetched_at?: string;
}

export interface RegimeState {
  regime: string;
  confidence: number;
  features: {
    trend_slope: number;
    atr_pct: number;
    atr_trend: number;
    ema_crossings: number;
  };
  detection_method: string;
}

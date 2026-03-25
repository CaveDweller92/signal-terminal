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
}

export interface SignalReasons {
  technical: string[];
  sentiment: string[];
  fundamental: string[];
}

export interface Signal {
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
  reasons: SignalReasons;
  indicators: Indicators;
}

export interface SignalListResponse {
  signals: Signal[];
  count: number;
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

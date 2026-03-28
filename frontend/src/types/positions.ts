export interface Position {
  id: number;
  symbol: string;
  exchange: string | null;
  direction: 'LONG' | 'SHORT';
  status: 'open' | 'closed';
  entry_price: number;
  quantity: number;
  entry_time: string;
  entry_signal_id: number | null;

  // Exit config
  stop_loss_price: number | null;
  profit_target_price: number | null;
  stop_loss_pct: number | null;
  profit_target_pct: number | null;
  use_atr_exits: boolean;
  atr_value_at_entry: number | null;
  eod_exit_enabled: boolean;
  max_hold_bars: number | null;

  // Live tracking
  current_price: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  high_since_entry: number | null;
  low_since_entry: number | null;
  bars_held: number;

  // Exit info (filled when closed)
  exit_price: number | null;
  exit_time: string | null;
  exit_reason: string | null;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  realized_pnl_dollar: number | null;

  // Context
  regime_at_entry: string | null;
  regime_at_exit: string | null;
  created_at: string;
}

export interface ExitSignal {
  id: number;
  position_id: number;
  symbol: string;
  exit_type: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  trigger_price: number | null;
  current_price: number;
  message: string;
  details: Record<string, unknown> | null;
  acknowledged: boolean;
  acted_on: boolean;
  created_at: string;
}

export interface TradeStats {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  avg_return_pct: number | null;
  avg_winner_pct: number | null;
  avg_loser_pct: number | null;
  best_trade_pct: number | null;
  worst_trade_pct: number | null;
  profit_factor: number | null;
  avg_bars_held: number | null;
}

export interface TradeInput {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entry_price: number;
  quantity: number;
  exchange?: string;
  stop_loss_price?: number;
  profit_target_price?: number;
  use_atr_exits?: boolean;
  eod_exit_enabled?: boolean;
}

export interface CloseInput {
  exit_price: number;
  exit_reason?: string;
}

// WebSocket message types
export interface WsExitAlert {
  type: 'exit_alert';
  alert: ExitSignal;
}

export interface WsPositionUpdate {
  type: 'position_update';
  position: Position;
}

export interface WsAck {
  type: 'ack';
  received: string;
}

export interface WsSignalUpdate {
  type: 'signal_update';
  signals: import('./market').Signal[];
  count: number;
  timestamp: string;
}

export type WsMessage = WsExitAlert | WsPositionUpdate | WsAck | WsSignalUpdate;

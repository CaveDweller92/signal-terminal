import type { ParameterSnapshot } from '../../types/adaptation';
import { StatBox } from '../common/StatBox';

interface CurrentParametersProps {
  snapshot: ParameterSnapshot;
}

export function CurrentParameters({ snapshot }: CurrentParametersProps) {
  const date = new Date(snapshot.created_at).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Current Parameters
        </span>
        <span className="text-[10px] font-mono text-zinc-600">
          {snapshot.snapshot_type}
          {snapshot.trigger ? ` · ${snapshot.trigger}` : ''}
          {' · '}{date}
        </span>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Entry</p>
        <div className="grid grid-cols-4 gap-2">
          <StatBox label="RSI Period" value={snapshot.rsi_period} />
          <StatBox label="RSI Oversold" value={snapshot.rsi_oversold} positive={true} />
          <StatBox label="RSI Overbought" value={snapshot.rsi_overbought} />
          <StatBox label="Vol Multiplier" value={`${snapshot.volume_multiplier}x`} />
          <StatBox label="EMA Fast" value={snapshot.ema_fast} />
          <StatBox label="EMA Slow" value={snapshot.ema_slow} />
          <StatBox label="Min Strength" value={snapshot.min_signal_strength.toFixed(1)} />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-2">
          <StatBox
            label="Tech Weight"
            value={`${(snapshot.technical_weight * 100).toFixed(0)}%`}
            positive={snapshot.technical_weight >= 0.4}
          />
          <StatBox
            label="Sentiment Weight"
            value={`${(snapshot.sentiment_weight * 100).toFixed(0)}%`}
          />
          <StatBox
            label="Fundamental Weight"
            value={`${(snapshot.fundamental_weight * 100).toFixed(0)}%`}
          />
        </div>
      </div>

      <div>
        <p className="text-[10px] uppercase tracking-wider text-zinc-600 mb-2">Exit</p>
        <div className="grid grid-cols-4 gap-2">
          <StatBox
            label="Stop Loss %"
            value={`${snapshot.default_stop_loss_pct.toFixed(1)}%`}
          />
          <StatBox
            label="Profit Target %"
            value={`${snapshot.default_profit_target_pct.toFixed(1)}%`}
            positive={true}
          />
          <StatBox
            label="ATR Stop ×"
            value={snapshot.atr_stop_multiplier.toFixed(2)}
          />
          <StatBox
            label="ATR Target ×"
            value={snapshot.atr_target_multiplier.toFixed(2)}
            positive={true}
          />
          <StatBox label="Max Hold Bars" value={snapshot.max_hold_days} />
          <StatBox
            label="R/R Ratio"
            value={(snapshot.default_profit_target_pct / snapshot.default_stop_loss_pct).toFixed(2)}
            positive={snapshot.default_profit_target_pct / snapshot.default_stop_loss_pct >= 1.5}
          />
        </div>
      </div>
    </div>
  );
}

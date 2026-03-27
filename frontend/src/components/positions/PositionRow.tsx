import type { Position } from '../../types/positions';
import { PnlBadge } from '../common/PnlBadge';

interface PositionRowProps {
  position: Position;
  onClose: (position: Position) => void;
}

export function PositionRow({ position, onClose }: PositionRowProps) {
  const directionColor =
    position.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400';

  return (
    <div className="px-4 py-3 border-b border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono font-bold text-zinc-100">
            {position.symbol}
          </span>
          <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${
            position.direction === 'LONG'
              ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
              : 'text-red-400 border-red-500/30 bg-red-500/10'
          }`}>
            {position.direction}
          </span>
          <span className="text-[10px] text-zinc-500 font-mono">
            {position.quantity} shares
          </span>
        </div>
        <PnlBadge
          pct={position.unrealized_pnl_pct}
          dollar={position.unrealized_pnl}
          size="md"
        />
      </div>

      <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
        <div className="flex gap-3">
          <span>
            Entry <span className="text-zinc-300">${position.entry_price.toFixed(2)}</span>
          </span>
          {position.current_price !== null && (
            <span>
              Now <span className="text-zinc-300">${position.current_price.toFixed(2)}</span>
            </span>
          )}
          {position.stop_loss_price !== null && (
            <span>
              SL <span className="text-red-400">${position.stop_loss_price.toFixed(2)}</span>
            </span>
          )}
          {position.profit_target_price !== null && (
            <span>
              PT <span className="text-emerald-400">${position.profit_target_price.toFixed(2)}</span>
            </span>
          )}
        </div>
        <button
          onClick={() => onClose(position)}
          className="text-[10px] text-zinc-400 hover:text-red-400 border border-zinc-700 hover:border-red-500/50 px-2 py-0.5 rounded transition-colors"
        >
          Close
        </button>
      </div>

      {position.bars_held > 0 && (
        <div className="mt-1 text-[10px] text-zinc-600 font-mono">
          {position.bars_held} bars held
          {position.regime_at_entry && (
            <span className="ml-2">· {position.regime_at_entry}</span>
          )}
        </div>
      )}
    </div>
  );
}

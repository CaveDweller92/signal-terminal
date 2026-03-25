import { SignalBadge } from '../common/SignalBadge';
import type { Signal } from '../../types/market';

interface WatchlistProps {
  signals: Signal[];
  selectedSymbol: string | null;
  onSelect: (symbol: string) => void;
}

export function Watchlist({ signals, selectedSymbol, onSelect }: WatchlistProps) {
  return (
    <aside className="w-72 border-r border-zinc-800 bg-zinc-900/50 flex flex-col">
      <div className="px-3 py-2 border-b border-zinc-800">
        <h2 className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
          Watchlist ({signals.length})
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {signals.map((signal) => (
          <button
            key={signal.symbol}
            onClick={() => onSelect(signal.symbol)}
            className={`w-full text-left px-3 py-2.5 border-b border-zinc-800/50 hover:bg-zinc-800/50 transition-colors ${
              selectedSymbol === signal.symbol ? 'bg-zinc-800/80 border-l-2 border-l-blue-500' : ''
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-mono font-semibold text-zinc-100">
                {signal.symbol}
              </span>
              <SignalBadge type={signal.signal_type} conviction={signal.conviction} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-zinc-400">
                ${signal.price_at_signal.toFixed(2)}
              </span>
              <span className="text-[10px] text-zinc-500 font-mono">
                RSI {signal.indicators.rsi.toFixed(0)}
              </span>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}

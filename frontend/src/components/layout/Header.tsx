import { RegimeBadge } from '../common/RegimeBadge';
import type { RegimeState } from '../../types/market';

interface HeaderProps {
  regime: RegimeState | null;
  onRefresh: () => void;
  loading: boolean;
}

export function Header({ regime, onRefresh, loading }: HeaderProps) {
  return (
    <header className="h-12 border-b border-zinc-800 bg-zinc-900/80 backdrop-blur flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-bold tracking-wide text-zinc-100">
          SIGNAL TERMINAL
        </h1>
        <span className="text-[10px] text-zinc-600 font-mono">v0.1</span>
      </div>

      <div className="flex items-center gap-3">
        {regime && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wider text-zinc-500">
              Market
            </span>
            <RegimeBadge regime={regime.regime} confidence={regime.confidence} />
          </div>
        )}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="text-xs text-zinc-400 hover:text-zinc-200 disabled:opacity-30 px-2 py-1 rounded border border-zinc-700 hover:border-zinc-600 transition-colors"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}

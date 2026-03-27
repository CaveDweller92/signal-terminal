import type { WatchlistEntry } from '../../types/discovery';
import { WatchlistCard } from './WatchlistCard';

interface WatchlistGridProps {
  picks: WatchlistEntry[];
  loading: boolean;
  onTriggerBuild: () => void;
  building: boolean;
  watchDate: string | null;
  source: string | null;
}

export function WatchlistGrid({
  picks,
  loading,
  onTriggerBuild,
  building,
  watchDate,
  source,
}: WatchlistGridProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-xs text-zinc-500">
        Loading watchlist...
      </div>
    );
  }

  const dateLabel = watchDate
    ? new Date(watchDate).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-zinc-500">
            {picks.length > 0 ? `${picks.length} picks` : 'No watchlist for today'}
          </span>
          {dateLabel && (
            <span className="text-[10px] text-zinc-600">· {dateLabel}</span>
          )}
          {source === 'ai' && (
            <span className="text-[10px] text-purple-400 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
              Claude-curated
            </span>
          )}
        </div>
        <button
          onClick={onTriggerBuild}
          disabled={building}
          className="text-[10px] text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-500 px-2.5 py-1 rounded transition-colors disabled:opacity-40"
        >
          {building ? 'Building...' : 'Build Watchlist'}
        </button>
      </div>

      {picks.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-2 text-zinc-600">
          <p className="text-xs">No watchlist built yet today.</p>
          <p className="text-[10px]">Run the screener first, then click "Build Watchlist".</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="grid grid-cols-2 gap-3">
            {picks.map((entry, i) => (
              <WatchlistCard key={entry.id} entry={entry} rank={i + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

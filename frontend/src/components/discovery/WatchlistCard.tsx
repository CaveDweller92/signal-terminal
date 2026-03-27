import type { WatchlistEntry } from '../../types/discovery';

interface WatchlistCardProps {
  entry: WatchlistEntry;
  rank: number;
}

export function WatchlistCard({ entry, rank }: WatchlistCardProps) {
  const isAI = entry.source === 'ai';

  return (
    <div className="bg-zinc-800/40 border border-zinc-700/50 rounded-lg p-3 hover:border-zinc-600 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-zinc-600">{rank}</span>
          <span className="text-sm font-mono font-bold text-zinc-100">{entry.symbol}</span>
          {entry.exchange && (
            <span className="text-[10px] text-zinc-600 font-mono">{entry.exchange}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          {isAI ? (
            <span className="text-[10px] font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
              AI pick
            </span>
          ) : (
            <span className="text-[10px] font-semibold text-zinc-400 bg-zinc-700/50 border border-zinc-600/30 px-1.5 py-0.5 rounded">
              screener
            </span>
          )}
        </div>
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-zinc-500">
        {entry.sector && <span>{entry.sector}</span>}
        {entry.sector && entry.regime_at_pick && <span>·</span>}
        {entry.regime_at_pick && (
          <span className="text-zinc-600">regime: {entry.regime_at_pick}</span>
        )}
        {entry.screener_rank !== null && (
          <>
            {(entry.sector || entry.regime_at_pick) && <span>·</span>}
            <span>screener #{entry.screener_rank}</span>
          </>
        )}
      </div>

      {/* AI reasoning */}
      {entry.ai_reasoning && (
        <p className="text-[11px] text-zinc-400 leading-relaxed border-l-2 border-purple-500/30 pl-2">
          {entry.ai_reasoning}
        </p>
      )}
    </div>
  );
}

import type { ScreenerResult } from '../../types/discovery';
import { ScoreBar } from './ScoreBar';

interface ScreenerTableProps {
  results: ScreenerResult[];
  loading: boolean;
  onTriggerScan: () => void;
  scanning: boolean;
}

const SCORE_DIMENSIONS: { key: keyof ScreenerResult; label: string }[] = [
  { key: 'volume_score', label: 'Volume' },
  { key: 'gap_score', label: 'Gap' },
  { key: 'technical_score', label: 'Technical' },
  { key: 'fundamental_score', label: 'Fundamental' },
  { key: 'news_score', label: 'News' },
  { key: 'sector_score', label: 'Sector' },
];

export function ScreenerTable({ results, loading, onTriggerScan, scanning }: ScreenerTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 text-xs text-zinc-500">
        Loading screener results...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-zinc-500">
          Top {results.length} stocks by composite score
        </span>
        <button
          onClick={onTriggerScan}
          disabled={scanning}
          className="text-[10px] text-zinc-400 hover:text-zinc-200 border border-zinc-700 hover:border-zinc-500 px-2.5 py-1 rounded transition-colors disabled:opacity-40"
        >
          {scanning ? 'Scanning...' : 'Run Scan'}
        </button>
      </div>

      {results.length === 0 ? (
        <div className="flex flex-col items-center justify-center flex-1 gap-2 text-zinc-600">
          <p className="text-xs">No screener results for today.</p>
          <p className="text-[10px]">Click "Run Scan" to scan the universe.</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          {results.map((result, rank) => (
            <ScreenerRow key={result.id} result={result} rank={rank + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function ScreenerRow({ result, rank }: { result: ScreenerResult; rank: number }) {
  return (
    <div className="px-4 py-3 border-b border-zinc-800/60 hover:bg-zinc-800/30 transition-colors">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-zinc-600 w-5">{rank}</span>
          <span className="text-sm font-mono font-bold text-zinc-100">{result.symbol}</span>
          {result.exchange && (
            <span className="text-[10px] text-zinc-600 font-mono">{result.exchange}</span>
          )}
          {result.sector && (
            <span className="text-[10px] text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded">
              {result.sector}
            </span>
          )}
          {result.has_catalyst && (
            <span className="text-[10px] text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 px-1.5 py-0.5 rounded">
              catalyst
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono text-zinc-400">
          {result.premarket_gap_pct !== null && (
            <span className={result.premarket_gap_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
              {result.premarket_gap_pct >= 0 ? '+' : ''}{result.premarket_gap_pct.toFixed(1)}% gap
            </span>
          )}
          {result.relative_volume !== null && (
            <span>{result.relative_volume.toFixed(1)}x vol</span>
          )}
          <span className="text-zinc-200 font-semibold">
            {result.composite_score.toFixed(3)}
          </span>
        </div>
      </div>

      {/* Score breakdown bars */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-1">
        {SCORE_DIMENSIONS.map(({ key, label }) => (
          <ScoreBar
            key={key}
            label={label}
            score={result[key] as number | null}
          />
        ))}
      </div>
    </div>
  );
}

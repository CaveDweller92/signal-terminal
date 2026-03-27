interface ScoreBarProps {
  score: number | null;
  max?: number;
  label?: string;
}

// Score is 0–1 range from backend
export function ScoreBar({ score, max = 1, label }: ScoreBarProps) {
  if (score === null) {
    return (
      <div className="flex items-center gap-1.5">
        {label && <span className="text-[10px] text-zinc-600 w-16 shrink-0">{label}</span>}
        <span className="text-[10px] text-zinc-600 font-mono">—</span>
      </div>
    );
  }

  const pct = Math.min(100, (score / max) * 100);
  const color =
    pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-1.5">
      {label && (
        <span className="text-[10px] text-zinc-500 w-16 shrink-0 truncate">{label}</span>
      )}
      <div className="flex-1 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-zinc-400 w-8 text-right shrink-0">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

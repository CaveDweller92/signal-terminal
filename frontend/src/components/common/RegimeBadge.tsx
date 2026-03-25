interface RegimeBadgeProps {
  regime: string;
  confidence: number;
}

const REGIME_STYLES: Record<string, string> = {
  trending_up: 'bg-emerald-500/20 text-emerald-400',
  trending_down: 'bg-red-500/20 text-red-400',
  mean_reverting: 'bg-amber-500/20 text-amber-400',
  volatile_choppy: 'bg-purple-500/20 text-purple-400',
  low_volatility: 'bg-blue-500/20 text-blue-400',
};

const REGIME_LABELS: Record<string, string> = {
  trending_up: 'Trending Up',
  trending_down: 'Trending Down',
  mean_reverting: 'Mean Reverting',
  volatile_choppy: 'Volatile/Choppy',
  low_volatility: 'Low Volatility',
};

export function RegimeBadge({ regime, confidence }: RegimeBadgeProps) {
  const style = REGIME_STYLES[regime] ?? 'bg-zinc-500/20 text-zinc-400';
  const label = REGIME_LABELS[regime] ?? regime;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono ${style}`}>
      {label}
      <span className="opacity-60">{(confidence * 100).toFixed(0)}%</span>
    </span>
  );
}

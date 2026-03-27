interface PnlBadgeProps {
  pct: number | null;
  dollar?: number | null;
  size?: 'sm' | 'md';
}

export function PnlBadge({ pct, dollar, size = 'sm' }: PnlBadgeProps) {
  if (pct === null) {
    return <span className="text-zinc-500 font-mono text-xs">—</span>;
  }

  const positive = pct >= 0;
  const color = positive ? 'text-emerald-400' : 'text-red-400';
  const textSize = size === 'md' ? 'text-sm' : 'text-xs';
  const sign = positive ? '+' : '';

  return (
    <span className={`font-mono font-semibold ${textSize} ${color}`}>
      {sign}{pct.toFixed(2)}%
      {dollar !== undefined && dollar !== null && (
        <span className="ml-1 opacity-60 text-[10px]">
          ({sign}${Math.abs(dollar).toFixed(2)})
        </span>
      )}
    </span>
  );
}

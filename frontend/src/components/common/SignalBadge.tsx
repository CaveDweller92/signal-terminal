interface SignalBadgeProps {
  type: 'BUY' | 'SELL' | 'HOLD';
  conviction: number;
}

const BADGE_STYLES = {
  BUY: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  SELL: 'bg-red-500/20 text-red-400 border-red-500/30',
  HOLD: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
} as const;

export function SignalBadge({ type, conviction }: SignalBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-mono font-semibold ${BADGE_STYLES[type]}`}
    >
      {type}
      <span className="text-[10px] opacity-70">{Math.abs(conviction).toFixed(1)}</span>
    </span>
  );
}

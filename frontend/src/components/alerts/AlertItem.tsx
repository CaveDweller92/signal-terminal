import type { ExitSignal } from '../../types/positions';

interface AlertItemProps {
  alert: ExitSignal;
}

const URGENCY_STYLES: Record<ExitSignal['urgency'], string> = {
  low: 'border-zinc-700 bg-zinc-800/30',
  medium: 'border-yellow-500/30 bg-yellow-500/5',
  high: 'border-orange-500/40 bg-orange-500/10',
  critical: 'border-red-500/60 bg-red-500/10 animate-pulse',
};

const URGENCY_LABEL: Record<ExitSignal['urgency'], string> = {
  low: 'text-zinc-400',
  medium: 'text-yellow-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
};

const EXIT_TYPE_ICONS: Record<string, string> = {
  stop_loss: '🛑',
  profit_target: '🎯',
  indicator_reversal: '↩',
  sentiment_shift: '📡',
  time_based: '⏱',
  eod: '🔔',
};

export function AlertItem({ alert }: AlertItemProps) {
  // Backend stores UTC without timezone suffix — append Z so the browser
  // correctly converts to the user's local time
  const utcTimestamp = alert.created_at.endsWith('Z') ? alert.created_at : `${alert.created_at}Z`;
  const timeStr = new Date(utcTimestamp).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const icon = EXIT_TYPE_ICONS[alert.exit_type] ?? '⚠';

  return (
    <div className={`px-3 py-2.5 border-b border-l-2 ${URGENCY_STYLES[alert.urgency]}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm flex-shrink-0">{icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-mono font-bold text-zinc-100">
                {alert.symbol}
              </span>
              <span className={`text-[10px] font-mono font-semibold uppercase ${URGENCY_LABEL[alert.urgency]}`}>
                {alert.urgency}
              </span>
            </div>
            <p className="text-xs text-zinc-300 mt-0.5 leading-snug">{alert.message}</p>
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <div className="text-[10px] font-mono text-zinc-500">{timeStr}</div>
          <div className="text-[10px] font-mono text-zinc-400 mt-0.5">
            ${alert.current_price.toFixed(2)}
          </div>
        </div>
      </div>

      {alert.trigger_price !== null && (
        <div className="mt-1 text-[10px] font-mono text-zinc-600">
          Trigger: ${alert.trigger_price.toFixed(2)}
        </div>
      )}
    </div>
  );
}

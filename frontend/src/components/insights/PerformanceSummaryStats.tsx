import type { PerformanceSummary } from '../../types/adaptation';
import { StatBox } from '../common/StatBox';

interface PerformanceSummaryStatsProps {
  summary: PerformanceSummary;
}

export function PerformanceSummaryStats({ summary }: PerformanceSummaryStatsProps) {
  const fmt = (v: number | null, suffix = '%') =>
    v !== null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}${suffix}` : '—';

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-4 gap-2">
        <StatBox
          label="Win Rate"
          value={summary.overall_win_rate !== null ? `${summary.overall_win_rate}%` : '—'}
          positive={summary.overall_win_rate !== null ? summary.overall_win_rate >= 50 : undefined}
        />
        <StatBox
          label="Avg Daily Return"
          value={fmt(summary.avg_daily_return_pct)}
          positive={summary.avg_daily_return_pct !== null ? summary.avg_daily_return_pct > 0 : undefined}
        />
        <StatBox
          label="Cumulative Return"
          value={fmt(summary.cumulative_return_pct)}
          positive={summary.cumulative_return_pct !== null ? summary.cumulative_return_pct > 0 : undefined}
        />
        <StatBox
          label="Total Signals"
          value={`${summary.total_correct} / ${summary.total_signals}`}
          subValue={`${summary.days}d window`}
        />
      </div>

      {(summary.best_day || summary.worst_day) && (
        <div className="grid grid-cols-2 gap-2">
          {summary.best_day && (
            <StatBox
              label="Best Day"
              value={fmt(summary.best_day.total_return_pct)}
              subValue={new Date(summary.best_day.perf_date).toLocaleDateString(undefined, {
                month: 'short', day: 'numeric',
              })}
              positive={true}
            />
          )}
          {summary.worst_day && (
            <StatBox
              label="Worst Day"
              value={fmt(summary.worst_day.total_return_pct)}
              subValue={new Date(summary.worst_day.perf_date).toLocaleDateString(undefined, {
                month: 'short', day: 'numeric',
              })}
              positive={false}
            />
          )}
        </div>
      )}
    </div>
  );
}

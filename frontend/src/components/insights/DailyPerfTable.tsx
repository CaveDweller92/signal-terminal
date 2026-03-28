import type { DailyPerformance } from '../../types/adaptation';

interface DailyPerfTableProps {
  records: DailyPerformance[];
}

export function DailyPerfTable({ records }: DailyPerfTableProps) {
  if (records.length === 0) {
    return (
      <div className="flex items-center justify-center py-10 text-xs text-zinc-600">
        No daily records yet. Computed nightly by the performance task.
      </div>
    );
  }

  return (
    <table className="w-full text-xs font-mono">
      <thead>
        <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-wider text-zinc-500">
          <th className="px-4 py-2 text-left">Date</th>
          <th className="px-2 py-2 text-right">Signals</th>
          <th className="px-2 py-2 text-right">Win Rate</th>
          <th className="px-2 py-2 text-right">Avg Return</th>
          <th className="px-2 py-2 text-right">Total Return</th>
          <th className="px-2 py-2 text-left">Regime</th>
        </tr>
      </thead>
      <tbody>
        {records.map((r) => (
          <DailyPerfRow key={r.id} record={r} />
        ))}
      </tbody>
    </table>
  );
}

function DailyPerfRow({ record }: { record: DailyPerformance }) {
  const date = new Date(record.perf_date).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric',
  });

  const winRate = record.win_rate !== null ? `${record.win_rate.toFixed(1)}%` : '—';
  const avgRet = record.avg_return_pct !== null
    ? `${record.avg_return_pct > 0 ? '+' : ''}${record.avg_return_pct.toFixed(2)}%`
    : '—';
  const totalRet = record.total_return_pct !== null
    ? `${record.total_return_pct > 0 ? '+' : ''}${record.total_return_pct.toFixed(2)}%`
    : '—';

  const retPositive = record.total_return_pct !== null ? record.total_return_pct > 0 : null;
  const retColor = retPositive === null
    ? 'text-zinc-400'
    : retPositive ? 'text-emerald-400' : 'text-red-400';

  const winPositive = record.win_rate !== null ? record.win_rate >= 50 : null;
  const winColor = winPositive === null
    ? 'text-zinc-400'
    : winPositive ? 'text-emerald-400' : 'text-red-400';

  return (
    <tr className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
      <td className="px-4 py-2 text-zinc-300">{date}</td>
      <td className="px-2 py-2 text-right text-zinc-400">
        {record.signals_correct}/{record.total_signals}
      </td>
      <td className={`px-2 py-2 text-right ${winColor}`}>{winRate}</td>
      <td className="px-2 py-2 text-right text-zinc-400">{avgRet}</td>
      <td className={`px-2 py-2 text-right font-semibold ${retColor}`}>{totalRet}</td>
      <td className="px-2 py-2 text-zinc-600 text-[10px]">{record.regime ?? '—'}</td>
    </tr>
  );
}

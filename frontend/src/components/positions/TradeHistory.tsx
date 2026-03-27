import { useState, useEffect } from 'react';
import type { Position, TradeStats } from '../../types/positions';
import { fetchTradeHistory, fetchTradeStats } from '../../services/api';
import { PnlBadge } from '../common/PnlBadge';
import { StatBox } from '../common/StatBox';

export function TradeHistory() {
  const [trades, setTrades] = useState<Position[]>([]);
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [t, s] = await Promise.all([fetchTradeHistory(), fetchTradeStats()]);
        if (!cancelled) {
          setTrades(t);
          setStats(s);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load history');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10 text-xs text-zinc-500">
        Loading history...
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-6 text-xs text-red-400 font-mono">{error}</div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {stats && stats.total_trades > 0 && (
        <div className="px-4 py-3 border-b border-zinc-800 grid grid-cols-4 gap-2">
          <StatBox
            label="Win Rate"
            value={stats.win_rate !== null ? `${stats.win_rate}%` : '—'}
            positive={stats.win_rate !== null ? stats.win_rate >= 50 : undefined}
          />
          <StatBox
            label="Avg Return"
            value={stats.avg_return_pct !== null ? `${stats.avg_return_pct > 0 ? '+' : ''}${stats.avg_return_pct}%` : '—'}
            positive={stats.avg_return_pct !== null ? stats.avg_return_pct > 0 : undefined}
          />
          <StatBox
            label="Profit Factor"
            value={stats.profit_factor !== null ? stats.profit_factor.toFixed(2) : '—'}
            positive={stats.profit_factor !== null ? stats.profit_factor >= 1 : undefined}
          />
          <StatBox
            label="Trades (30d)"
            value={stats.total_trades}
          />
        </div>
      )}

      {trades.length === 0 ? (
        <div className="px-4 py-6 text-center text-xs text-zinc-500">
          No closed trades in the last 30 days.
        </div>
      ) : (
        <table className="w-full text-xs font-mono">
          <thead>
            <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-wider text-zinc-500">
              <th className="px-4 py-2 text-left">Symbol</th>
              <th className="px-2 py-2 text-left">Dir</th>
              <th className="px-2 py-2 text-right">Entry</th>
              <th className="px-2 py-2 text-right">Exit</th>
              <th className="px-2 py-2 text-right">P&L</th>
              <th className="px-2 py-2 text-left">Reason</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <TradeRow key={trade.id} trade={trade} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function TradeRow({ trade }: { trade: Position }) {
  const exitTime = trade.exit_time
    ? new Date(trade.exit_time).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })
    : '—';

  return (
    <tr className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
      <td className="px-4 py-2">
        <span className="font-semibold text-zinc-100">{trade.symbol}</span>
        <span className="block text-[10px] text-zinc-600">{exitTime}</span>
      </td>
      <td className="px-2 py-2">
        <span className={trade.direction === 'LONG' ? 'text-emerald-400' : 'text-red-400'}>
          {trade.direction}
        </span>
      </td>
      <td className="px-2 py-2 text-right text-zinc-300">
        ${trade.entry_price.toFixed(2)}
      </td>
      <td className="px-2 py-2 text-right text-zinc-300">
        {trade.exit_price !== null ? `$${trade.exit_price.toFixed(2)}` : '—'}
      </td>
      <td className="px-2 py-2 text-right">
        <PnlBadge pct={trade.realized_pnl_pct} dollar={trade.realized_pnl_dollar} />
      </td>
      <td className="px-2 py-2 text-zinc-500 text-[10px]">
        {trade.exit_reason ?? '—'}
      </td>
    </tr>
  );
}

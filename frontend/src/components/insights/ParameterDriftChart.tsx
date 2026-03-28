import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { ParameterSnapshot } from '../../types/adaptation';

interface ParameterDriftChartProps {
  snapshots: ParameterSnapshot[];
}

interface ChartPoint {
  date: string;
  stop_loss_pct: number;
  profit_target_pct: number;
  atr_stop: number;
  atr_target: number;
  rsi_oversold: number;
  rsi_overbought: number;
}

const LINES: { key: keyof ChartPoint; label: string; color: string; dashed?: boolean }[] = [
  { key: 'stop_loss_pct', label: 'Stop Loss %', color: '#f87171' },
  { key: 'profit_target_pct', label: 'Profit Target %', color: '#34d399' },
  { key: 'atr_stop', label: 'ATR Stop ×', color: '#fb923c', dashed: true },
  { key: 'atr_target', label: 'ATR Target ×', color: '#60a5fa', dashed: true },
];

export function ParameterDriftChart({ snapshots }: ParameterDriftChartProps) {
  if (snapshots.length === 0) {
    return (
      <EmptyState message="No parameter history yet. Snapshots are saved after each closed trade." />
    );
  }

  // Oldest first for the chart
  const data: ChartPoint[] = [...snapshots].reverse().map((s) => ({
    date: new Date(s.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    stop_loss_pct: s.default_stop_loss_pct,
    profit_target_pct: s.default_profit_target_pct,
    atr_stop: s.atr_stop_multiplier,
    atr_target: s.atr_target_multiplier,
    rsi_oversold: s.rsi_oversold,
    rsi_overbought: s.rsi_overbought,
  }));

  return (
    <div className="space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
        Parameter Drift — {snapshots.length} snapshots
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#71717a', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fill: '#71717a', fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#18181b',
              border: '1px solid #3f3f46',
              borderRadius: 6,
              fontSize: 11,
              fontFamily: 'monospace',
            }}
            labelStyle={{ color: '#a1a1aa' }}
          />
          <Legend
            wrapperStyle={{ fontSize: 10, color: '#71717a', paddingTop: 8 }}
          />
          {LINES.map(({ key, label, color, dashed }) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              name={label}
              stroke={color}
              strokeWidth={1.5}
              strokeDasharray={dashed ? '4 2' : undefined}
              dot={false}
              activeDot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-32 text-xs text-zinc-600">
      {message}
    </div>
  );
}

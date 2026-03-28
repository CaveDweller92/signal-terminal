import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import type { DailyPerformance } from '../../types/adaptation';

interface EquityCurveProps {
  daily: DailyPerformance[];
}

interface ChartPoint {
  date: string;
  cumulative: number;
  daily: number;
}

export function EquityCurve({ daily }: EquityCurveProps) {
  if (daily.length === 0) {
    return (
      <div className="flex items-center justify-center h-36 text-xs text-zinc-600">
        No performance data yet. Records are computed nightly.
      </div>
    );
  }

  // daily arrives newest-first; reverse for chart
  const sorted = [...daily].reverse();
  let cumulative = 0;
  const data: ChartPoint[] = sorted.map((d) => {
    cumulative += d.total_return_pct ?? 0;
    return {
      date: new Date(d.perf_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      cumulative: parseFloat(cumulative.toFixed(2)),
      daily: d.total_return_pct ?? 0,
    };
  });

  const isPositive = cumulative >= 0;
  const fillColor = isPositive ? '#34d399' : '#f87171';
  const strokeColor = isPositive ? '#10b981' : '#ef4444';

  return (
    <div className="space-y-1">
      <p className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
        Equity Curve — {daily.length}d cumulative return
        <span className={`ml-2 font-mono ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {isPositive ? '+' : ''}{cumulative.toFixed(2)}%
        </span>
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={fillColor} stopOpacity={0.2} />
              <stop offset="95%" stopColor={fillColor} stopOpacity={0} />
            </linearGradient>
          </defs>
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
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v}%`}
          />
          <ReferenceLine y={0} stroke="#52525b" strokeDasharray="3 3" />
          <Tooltip
            contentStyle={{
              backgroundColor: '#18181b',
              border: '1px solid #3f3f46',
              borderRadius: 6,
              fontSize: 11,
              fontFamily: 'monospace',
            }}
            labelStyle={{ color: '#a1a1aa' }}
            formatter={(value: number, name: string) => [
              `${value > 0 ? '+' : ''}${value.toFixed(2)}%`,
              name === 'cumulative' ? 'Cumulative' : 'Daily',
            ]}
          />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={strokeColor}
            strokeWidth={2}
            fill="url(#equityFill)"
            dot={false}
            activeDot={{ r: 3, fill: strokeColor }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

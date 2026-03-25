interface StatBoxProps {
  label: string;
  value: string | number;
  subValue?: string;
  positive?: boolean;
}

export function StatBox({ label, value, subValue, positive }: StatBoxProps) {
  const valueColor = positive === undefined
    ? 'text-zinc-100'
    : positive
      ? 'text-emerald-400'
      : 'text-red-400';

  return (
    <div className="bg-zinc-800/50 rounded-lg px-3 py-2 border border-zinc-700/50">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500 mb-0.5">
        {label}
      </div>
      <div className={`text-sm font-mono font-semibold ${valueColor}`}>
        {value}
      </div>
      {subValue && (
        <div className="text-[10px] text-zinc-500 mt-0.5">{subValue}</div>
      )}
    </div>
  );
}

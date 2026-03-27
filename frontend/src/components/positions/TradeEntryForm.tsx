import { useState } from 'react';
import type { TradeInput } from '../../types/positions';

interface TradeEntryFormProps {
  onSubmit: (trade: TradeInput) => Promise<void>;
  prefillSymbol?: string;
  prefillPrice?: number;
}

type Direction = 'LONG' | 'SHORT';

interface FormState {
  symbol: string;
  direction: Direction;
  entry_price: string;
  quantity: string;
  stop_loss_price: string;
  profit_target_price: string;
  use_atr_exits: boolean;
  eod_exit_enabled: boolean;
}

const INITIAL: FormState = {
  symbol: '',
  direction: 'LONG',
  entry_price: '',
  quantity: '',
  stop_loss_price: '',
  profit_target_price: '',
  use_atr_exits: true,
  eod_exit_enabled: true,
};

export function TradeEntryForm({ onSubmit, prefillSymbol, prefillPrice }: TradeEntryFormProps) {
  const [form, setForm] = useState<FormState>({
    ...INITIAL,
    symbol: prefillSymbol ?? '',
    entry_price: prefillPrice?.toFixed(2) ?? '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  function set(field: keyof FormState, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const trade: TradeInput = {
      symbol: form.symbol.toUpperCase().trim(),
      direction: form.direction,
      entry_price: parseFloat(form.entry_price),
      quantity: parseInt(form.quantity, 10),
      use_atr_exits: form.use_atr_exits,
      eod_exit_enabled: form.eod_exit_enabled,
    };

    if (form.stop_loss_price) trade.stop_loss_price = parseFloat(form.stop_loss_price);
    if (form.profit_target_price) trade.profit_target_price = parseFloat(form.profit_target_price);

    if (!trade.symbol || isNaN(trade.entry_price) || isNaN(trade.quantity)) {
      setError('Symbol, entry price, and quantity are required.');
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(trade);
      setForm(INITIAL);
      setExpanded(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open position');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="border-b border-zinc-800">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition-colors"
      >
        <span className="uppercase tracking-wider">+ New Trade</span>
        <span className="text-zinc-600">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <form onSubmit={handleSubmit} className="px-4 pb-4 space-y-2.5">
          {/* Row 1: Symbol + Direction */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Symbol
              </label>
              <input
                type="text"
                value={form.symbol}
                onChange={(e) => set('symbol', e.target.value)}
                placeholder="AAPL"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm font-mono text-zinc-100 uppercase placeholder:normal-case placeholder:text-zinc-600 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Direction
              </label>
              <div className="flex">
                {(['LONG', 'SHORT'] as Direction[]).map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => set('direction', d)}
                    className={`px-3 py-1.5 text-xs font-mono font-semibold border transition-colors first:rounded-l last:rounded-r ${
                      form.direction === d
                        ? d === 'LONG'
                          ? 'bg-emerald-600 border-emerald-500 text-white'
                          : 'bg-red-600 border-red-500 text-white'
                        : 'bg-zinc-800 border-zinc-700 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Row 2: Price + Quantity */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Entry Price
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={form.entry_price}
                onChange={(e) => set('entry_price', e.target.value)}
                placeholder="0.00"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div className="flex-1">
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Shares
              </label>
              <input
                type="number"
                step="1"
                min="1"
                value={form.quantity}
                onChange={(e) => set('quantity', e.target.value)}
                placeholder="100"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
          </div>

          {/* Optional overrides toggle */}
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="hidden"
          />
          <details className="text-[10px] text-zinc-500">
            <summary className="cursor-pointer hover:text-zinc-300 transition-colors py-0.5">
              Override stop / target (optional)
            </summary>
            <div className="flex gap-2 mt-2">
              <div className="flex-1">
                <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                  Stop Loss $
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.stop_loss_price}
                  onChange={(e) => set('stop_loss_price', e.target.value)}
                  placeholder="auto"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="flex-1">
                <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                  Profit Target $
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.profit_target_price}
                  onChange={(e) => set('profit_target_price', e.target.value)}
                  placeholder="auto"
                  className="w-full bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex gap-4 mt-2">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.use_atr_exits}
                  onChange={(e) => set('use_atr_exits', e.target.checked)}
                  className="accent-blue-500"
                />
                ATR exits
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.eod_exit_enabled}
                  onChange={(e) => set('eod_exit_enabled', e.target.checked)}
                  className="accent-blue-500"
                />
                EOD exit
              </label>
            </div>
          </details>

          {error && (
            <p className="text-xs text-red-400 font-mono">{error}</p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full text-xs font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white rounded py-1.5 transition-colors"
          >
            {submitting ? 'Opening...' : 'Open Position'}
          </button>
        </form>
      )}
    </div>
  );
}

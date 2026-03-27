import { useState } from 'react';
import type { Position, CloseInput } from '../../types/positions';

interface ClosePositionModalProps {
  position: Position;
  onConfirm: (id: number, input: CloseInput) => Promise<void>;
  onCancel: () => void;
}

export function ClosePositionModal({
  position,
  onConfirm,
  onCancel,
}: ClosePositionModalProps) {
  const [exitPrice, setExitPrice] = useState(
    position.current_price?.toFixed(2) ?? position.entry_price.toFixed(2)
  );
  const [exitReason, setExitReason] = useState('manual');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedPrice = parseFloat(exitPrice);
  const isValid = !isNaN(parsedPrice) && parsedPrice > 0;

  const estimatedPnlPct = isValid
    ? ((parsedPrice - position.entry_price) / position.entry_price) *
      100 *
      (position.direction === 'SHORT' ? -1 : 1)
    : null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(position.id, { exit_price: parsedPrice, exit_reason: exitReason });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to close position');
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-80 p-5 shadow-xl">
        <h2 className="text-sm font-mono font-bold text-zinc-100 mb-4">
          Close {position.symbol}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
              Exit Price
            </label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={exitPrice}
              onChange={(e) => setExitPrice(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
              Reason
            </label>
            <select
              value={exitReason}
              onChange={(e) => setExitReason(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
            >
              <option value="manual">Manual</option>
              <option value="stop_loss">Stop Loss</option>
              <option value="profit_target">Profit Target</option>
              <option value="eod">End of Day</option>
              <option value="other">Other</option>
            </select>
          </div>

          {estimatedPnlPct !== null && (
            <div className="text-[10px] font-mono text-center py-1 rounded bg-zinc-800">
              Estimated P&L:{' '}
              <span className={estimatedPnlPct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                {estimatedPnlPct >= 0 ? '+' : ''}{estimatedPnlPct.toFixed(2)}%
              </span>
            </div>
          )}

          {error && (
            <p className="text-xs text-red-400 font-mono">{error}</p>
          )}

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 text-xs text-zinc-400 border border-zinc-700 rounded py-1.5 hover:border-zinc-500 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isValid || submitting}
              className="flex-1 text-xs text-white bg-red-600 hover:bg-red-500 disabled:opacity-40 rounded py-1.5 font-semibold transition-colors"
            >
              {submitting ? 'Closing...' : 'Close Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

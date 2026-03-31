import { useState } from 'react';
import type { Position } from '../../types/positions';
import { editPosition } from '../../services/api';

interface EditPositionModalProps {
  position: Position;
  onSave: (updated: Position) => void;
  onCancel: () => void;
}

export function EditPositionModal({ position, onSave, onCancel }: EditPositionModalProps) {
  const [entryPrice, setEntryPrice] = useState(position.entry_price.toFixed(2));
  const [quantity, setQuantity] = useState(String(position.quantity));
  const [direction, setDirection] = useState(position.direction);
  const [stopLoss, setStopLoss] = useState(position.stop_loss_price?.toFixed(2) ?? '');
  const [profitTarget, setProfitTarget] = useState(position.profit_target_price?.toFixed(2) ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedEntry = parseFloat(entryPrice);
  const parsedQty = parseInt(quantity, 10);
  const isValid = !isNaN(parsedEntry) && parsedEntry > 0 && !isNaN(parsedQty) && parsedQty > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid) return;
    setSubmitting(true);
    setError(null);

    const updates: Record<string, unknown> = {};
    if (parsedEntry !== position.entry_price) updates.entry_price = parsedEntry;
    if (parsedQty !== position.quantity) updates.quantity = parsedQty;
    if (direction !== position.direction) updates.direction = direction;
    const sl = parseFloat(stopLoss);
    if (!isNaN(sl) && sl !== position.stop_loss_price) updates.stop_loss_price = sl;
    const pt = parseFloat(profitTarget);
    if (!isNaN(pt) && pt !== position.profit_target_price) updates.profit_target_price = pt;

    if (Object.keys(updates).length === 0) {
      onCancel();
      return;
    }

    try {
      const updated = await editPosition(position.id, updates);
      onSave(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update position');
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg w-96 p-5 shadow-xl">
        <h2 className="text-sm font-mono font-bold text-zinc-100 mb-4">
          Edit {position.symbol}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Entry Price
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={entryPrice}
                onChange={(e) => setEntryPrice(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Quantity
              </label>
              <input
                type="number"
                step="1"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
              Direction
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setDirection('LONG')}
                className={`flex-1 text-xs font-semibold py-1.5 rounded border transition-colors ${
                  direction === 'LONG'
                    ? 'text-emerald-400 border-emerald-500/50 bg-emerald-500/10'
                    : 'text-zinc-500 border-zinc-700 hover:border-zinc-500'
                }`}
              >
                LONG
              </button>
              <button
                type="button"
                onClick={() => setDirection('SHORT')}
                className={`flex-1 text-xs font-semibold py-1.5 rounded border transition-colors ${
                  direction === 'SHORT'
                    ? 'text-red-400 border-red-500/50 bg-red-500/10'
                    : 'text-zinc-500 border-zinc-700 hover:border-zinc-500'
                }`}
              >
                SHORT
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Stop Loss
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                placeholder="Optional"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-zinc-500 mb-1">
                Profit Target
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={profitTarget}
                onChange={(e) => setProfitTarget(e.target.value)}
                placeholder="Optional"
                className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-1.5 text-sm font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

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
              className="flex-1 text-xs text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded py-1.5 font-semibold transition-colors"
            >
              {submitting ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

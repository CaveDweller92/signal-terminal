import { useState } from 'react';
import type { Position, CloseInput, TradeInput } from '../../types/positions';
import { PositionRow } from './PositionRow';
import { ClosePositionModal } from './ClosePositionModal';
import { EditPositionModal } from './EditPositionModal';
import { TradeEntryForm } from './TradeEntryForm';

interface PositionListProps {
  positions: Position[];
  loading: boolean;
  onOpen: (trade: TradeInput) => Promise<void>;
  onClose: (id: number, input: CloseInput) => Promise<void>;
  onEdit: (updated: Position) => void;
}

export function PositionList({ positions, loading, onOpen, onClose, onEdit }: PositionListProps) {
  const [closingPosition, setClosingPosition] = useState<Position | null>(null);
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);

  return (
    <div className="flex flex-col h-full">
      <TradeEntryForm onSubmit={onOpen} />

      <div className="flex-1 overflow-y-auto">
        {loading && positions.length === 0 && (
          <div className="px-4 py-6 text-center text-xs text-zinc-500">
            Loading positions...
          </div>
        )}

        {!loading && positions.length === 0 && (
          <div className="px-4 py-6 text-center text-xs text-zinc-500">
            No open positions. Use the form above to enter a trade.
          </div>
        )}

        {positions.map((position) => (
          <PositionRow
            key={position.id}
            position={position}
            onEdit={setEditingPosition}
            onClose={setClosingPosition}
          />
        ))}
      </div>

      {closingPosition && (
        <ClosePositionModal
          position={closingPosition}
          onConfirm={async (id, input) => {
            await onClose(id, input);
            setClosingPosition(null);
          }}
          onCancel={() => setClosingPosition(null)}
        />
      )}

      {editingPosition && (
        <EditPositionModal
          position={editingPosition}
          onSave={(updated) => {
            onEdit(updated);
            setEditingPosition(null);
          }}
          onCancel={() => setEditingPosition(null)}
        />
      )}
    </div>
  );
}

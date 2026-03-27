import { useState } from 'react';
import type { Position, CloseInput, TradeInput } from '../../types/positions';
import { PositionList } from './PositionList';
import { TradeHistory } from './TradeHistory';

type TabId = 'open' | 'history';

interface PositionsPanelProps {
  positions: Position[];
  loading: boolean;
  onOpen: (trade: TradeInput) => Promise<void>;
  onClose: (id: number, input: CloseInput) => Promise<void>;
}

export function PositionsPanel({ positions, loading, onOpen, onClose }: PositionsPanelProps) {
  const [tab, setTab] = useState<TabId>('open');

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Tab bar */}
      <div className="border-b border-zinc-800 px-4 flex gap-1">
        <TabButton id="open" active={tab === 'open'} onClick={setTab}>
          Open{positions.length > 0 && (
            <span className="ml-1.5 text-[10px] bg-blue-500/20 text-blue-400 px-1.5 rounded-full">
              {positions.length}
            </span>
          )}
        </TabButton>
        <TabButton id="history" active={tab === 'history'} onClick={setTab}>
          History
        </TabButton>
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === 'open' && (
          <PositionList
            positions={positions}
            loading={loading}
            onOpen={onOpen}
            onClose={onClose}
          />
        )}
        {tab === 'history' && <TradeHistory />}
      </div>
    </div>
  );
}

interface TabButtonProps {
  id: TabId;
  active: boolean;
  onClick: (id: TabId) => void;
  children: React.ReactNode;
}

function TabButton({ id, active, onClick, children }: TabButtonProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`px-3 py-2 text-xs font-semibold transition-colors border-b-2 ${
        active
          ? 'text-blue-400 border-blue-400'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {children}
    </button>
  );
}

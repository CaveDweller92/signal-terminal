import { useState } from 'react';
import { AdaptationPanel } from './AdaptationPanel';
import { PerformancePanel } from './PerformancePanel';

type TabId = 'performance' | 'adaptation';

export function InsightsPanel() {
  const [tab, setTab] = useState<TabId>('performance');

  return (
    <div className="flex flex-col h-full">
      {/* Top-level section switcher */}
      <div className="border-b border-zinc-800 bg-zinc-900/40 px-4 flex gap-4">
        <SectionButton id="performance" active={tab === 'performance'} onClick={setTab}>
          Performance
        </SectionButton>
        <SectionButton id="adaptation" active={tab === 'adaptation'} onClick={setTab}>
          Adaptation
        </SectionButton>
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === 'performance' && <PerformancePanel />}
        {tab === 'adaptation' && <AdaptationPanel />}
      </div>
    </div>
  );
}

interface SectionButtonProps {
  id: TabId;
  active: boolean;
  onClick: (id: TabId) => void;
  children: React.ReactNode;
}

function SectionButton({ id, active, onClick, children }: SectionButtonProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`py-2 text-xs font-semibold transition-colors border-b-2 ${
        active
          ? 'text-zinc-100 border-blue-400'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {children}
    </button>
  );
}

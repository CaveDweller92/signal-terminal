import { useState, useEffect } from 'react';
import type { PerformanceSummary } from '../../types/adaptation';
import { fetchPerformanceSummary } from '../../services/api';
import { EquityCurve } from './EquityCurve';
import { PerformanceSummaryStats } from './PerformanceSummaryStats';
import { DailyPerfTable } from './DailyPerfTable';

type TabId = 'overview' | 'daily';
type Window = 7 | 30 | 90;

const WINDOWS: Window[] = [7, 30, 90];

export function PerformancePanel() {
  const [tab, setTab] = useState<TabId>('overview');
  const [window, setWindow] = useState<Window>(30);
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await fetchPerformanceSummary(window);
        if (!cancelled) setSummary(data);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [window]);

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Tab bar + window picker */}
      <div className="border-b border-zinc-800 px-4 flex items-center justify-between">
        <div className="flex gap-1">
          <TabButton id="overview" active={tab === 'overview'} onClick={setTab}>
            Overview
          </TabButton>
          <TabButton id="daily" active={tab === 'daily'} onClick={setTab}>
            Daily
          </TabButton>
        </div>
        <div className="flex gap-1">
          {WINDOWS.map((w) => (
            <button
              key={w}
              onClick={() => setWindow(w)}
              className={`px-2 py-1 text-[10px] font-mono rounded transition-colors ${
                window === w
                  ? 'bg-zinc-700 text-zinc-100'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {w}d
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-xs text-zinc-500">
            Loading performance data...
          </div>
        ) : summary === null ? (
          <div className="flex items-center justify-center h-full text-xs text-zinc-600">
            No performance records found.
          </div>
        ) : (
          <>
            {tab === 'overview' && (
              <div className="p-4 space-y-6">
                <PerformanceSummaryStats summary={summary} />
                <div className="border-t border-zinc-800 pt-4">
                  <EquityCurve daily={summary.daily} />
                </div>
              </div>
            )}
            {tab === 'daily' && (
              <DailyPerfTable records={summary.daily} />
            )}
          </>
        )}
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
      className={`flex items-center px-3 py-2 text-xs font-semibold transition-colors border-b-2 ${
        active
          ? 'text-blue-400 border-blue-400'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {children}
    </button>
  );
}

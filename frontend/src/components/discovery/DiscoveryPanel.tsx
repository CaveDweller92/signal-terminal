import { useState, useEffect, useCallback } from 'react';
import type { ScreenerResult, WatchlistEntry } from '../../types/discovery';
import {
  fetchScreenerResults,
  fetchWatchlist,
  triggerScan,
  triggerWatchlistBuild,
} from '../../services/api';
import { ScreenerTable } from './ScreenerTable';
import { WatchlistGrid } from './WatchlistGrid';

type TabId = 'watchlist' | 'screener';

export function DiscoveryPanel() {
  const [tab, setTab] = useState<TabId>('watchlist');

  const [screenerResults, setScreenerResults] = useState<ScreenerResult[]>([]);
  const [screenerLoading, setScreenerLoading] = useState(true);
  const [scanning, setScanning] = useState(false);

  const [watchlistPicks, setWatchlistPicks] = useState<WatchlistEntry[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(true);
  const [building, setBuilding] = useState(false);
  const [watchDate, setWatchDate] = useState<string | null>(null);
  const [watchSource, setWatchSource] = useState<string | null>(null);

  const loadScreener = useCallback(async () => {
    setScreenerLoading(true);
    try {
      const data = await fetchScreenerResults();
      setScreenerResults(data.results);
    } finally {
      setScreenerLoading(false);
    }
  }, []);

  const loadWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    try {
      const data = await fetchWatchlist();
      setWatchlistPicks(data.picks);
      setWatchDate(data.watch_date);
      setWatchSource(data.picks.length > 0 ? data.picks[0].source : null);
    } finally {
      setWatchlistLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadScreener();
    void loadWatchlist();
  }, [loadScreener, loadWatchlist]);

  async function handleScan() {
    setScanning(true);
    try {
      await triggerScan();
      await loadScreener();
    } finally {
      setScanning(false);
    }
  }

  async function handleBuildWatchlist() {
    setBuilding(true);
    try {
      await triggerWatchlistBuild();
      await loadWatchlist();
    } finally {
      setBuilding(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Tab bar */}
      <div className="border-b border-zinc-800 px-4 flex gap-1">
        <TabButton id="watchlist" active={tab === 'watchlist'} onClick={setTab}>
          AI Watchlist
          {watchlistPicks.length > 0 && (
            <span className="ml-1.5 text-[10px] bg-purple-500/20 text-purple-400 px-1.5 rounded-full">
              {watchlistPicks.length}
            </span>
          )}
        </TabButton>
        <TabButton id="screener" active={tab === 'screener'} onClick={setTab}>
          Screener
          {screenerResults.length > 0 && (
            <span className="ml-1.5 text-[10px] bg-zinc-700 text-zinc-400 px-1.5 rounded-full">
              {screenerResults.length}
            </span>
          )}
        </TabButton>
      </div>

      <div className="flex-1 overflow-hidden">
        {tab === 'watchlist' && (
          <WatchlistGrid
            picks={watchlistPicks}
            loading={watchlistLoading}
            onTriggerBuild={handleBuildWatchlist}
            building={building}
            watchDate={watchDate}
            source={watchSource}
          />
        )}
        {tab === 'screener' && (
          <ScreenerTable
            results={screenerResults}
            loading={screenerLoading}
            onTriggerScan={handleScan}
            scanning={scanning}
          />
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

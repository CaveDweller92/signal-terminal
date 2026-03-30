import { useState, useEffect } from 'react';
import { Header } from './components/layout/Header';
import { Watchlist } from './components/layout/Watchlist';
import { DetailPanel } from './components/layout/DetailPanel';
import { PositionsPanel } from './components/positions/PositionsPanel';
import { AlertFeed } from './components/alerts/AlertFeed';
import { DiscoveryPanel } from './components/discovery/DiscoveryPanel';
import { InsightsPanel } from './components/insights/InsightsPanel';
import { useSignals } from './hooks/useSignals';
import { useRegime } from './hooks/useRegime';
import { usePositions } from './hooks/usePositions';
import { useWebSocket } from './hooks/useWebSocket';

type MainTab = 'signals' | 'positions' | 'alerts' | 'discovery' | 'insights';

function App() {
  const { signals, loading, error, secondsUntilRefresh, refresh: refreshSignals, applyLiveUpdate } = useSignals();
  const { regime, refresh: refreshRegime } = useRegime();
  const { positions, loading: posLoading, refresh: refreshPositions, addPosition, closePos, updatePosition } = usePositions();
  const { connected, alerts, clearAlerts, onPositionUpdate, onSignalUpdate } = useWebSocket();

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<MainTab>('signals');

  // Load positions on mount
  useEffect(() => {
    void refreshPositions();
  }, [refreshPositions]);

  // Route WebSocket position_update messages to the positions state
  useEffect(() => {
    onPositionUpdate((msg) => {
      if (msg.type === 'position_update') {
        updatePosition(msg.position);
      }
    });
  }, [onPositionUpdate, updatePosition]);

  // Route WebSocket signal_update messages to the signals state
  useEffect(() => {
    onSignalUpdate(applyLiveUpdate);
  }, [onSignalUpdate, applyLiveUpdate]);

  // Switch to alerts tab automatically when a critical alert arrives
  useEffect(() => {
    const latest = alerts[0];
    if (latest?.urgency === 'critical') {
      setMainTab('alerts');
    }
  }, [alerts]);

  const selectedSignal = signals.find((s) => s.symbol === selectedSymbol) ?? null;
  const unreadAlerts = alerts.length;

  function handleRefresh() {
    refreshSignals();
    refreshRegime();
  }

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100">
      <Header regime={regime} onRefresh={handleRefresh} loading={loading} />

      {/* Main tab bar */}
      <div className="border-b border-zinc-800 bg-zinc-900/60 flex items-center px-4 gap-1">
        <MainTabButton id="signals" active={mainTab === 'signals'} onClick={setMainTab}>
          Signals
        </MainTabButton>
        <MainTabButton id="positions" active={mainTab === 'positions'} onClick={setMainTab}>
          Positions
          {positions.length > 0 && (
            <span className="ml-1.5 text-[10px] bg-blue-500/20 text-blue-400 px-1.5 rounded-full">
              {positions.length}
            </span>
          )}
        </MainTabButton>
        <MainTabButton id="alerts" active={mainTab === 'alerts'} onClick={setMainTab}>
          Alerts
          {unreadAlerts > 0 && (
            <span className="ml-1.5 text-[10px] bg-red-500/20 text-red-400 px-1.5 rounded-full">
              {unreadAlerts}
            </span>
          )}
        </MainTabButton>
        <MainTabButton id="discovery" active={mainTab === 'discovery'} onClick={setMainTab}>
          Discovery
        </MainTabButton>
        <MainTabButton id="insights" active={mainTab === 'insights'} onClick={setMainTab}>
          Insights
        </MainTabButton>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {mainTab === 'signals' && (
          <>
            <Watchlist
              signals={signals}
              selectedSymbol={selectedSymbol}
              onSelect={setSelectedSymbol}
              secondsUntilRefresh={secondsUntilRefresh}
            />
            <main className="flex-1 flex">
              {error && (
                <div className="flex-1 flex items-center justify-center">
                  <div className="text-center">
                    <p className="text-red-400 text-sm mb-2">Failed to load signals</p>
                    <p className="text-zinc-500 text-xs font-mono">{error}</p>
                    <button
                      onClick={handleRefresh}
                      className="mt-3 text-xs text-blue-400 hover:text-blue-300"
                    >
                      Try again
                    </button>
                  </div>
                </div>
              )}
              {!error && !selectedSignal && (
                <div className="flex-1 flex items-center justify-center">
                  <p className="text-zinc-500 text-sm">
                    {loading ? 'Loading signals...' : 'Select a stock from the watchlist'}
                  </p>
                </div>
              )}
              {!error && selectedSignal && <DetailPanel signal={selectedSignal} />}
            </main>
          </>
        )}

        {mainTab === 'positions' && (
          <div className="flex-1 overflow-hidden">
            <PositionsPanel
              positions={positions}
              loading={posLoading}
              onOpen={addPosition}
              onClose={closePos}
            />
          </div>
        )}

        {mainTab === 'alerts' && (
          <div className="flex-1 overflow-hidden">
            <AlertFeed
              alerts={alerts}
              connected={connected}
              onClear={clearAlerts}
            />
          </div>
        )}

        {mainTab === 'discovery' && (
          <div className="flex-1 overflow-hidden">
            <DiscoveryPanel />
          </div>
        )}

        {mainTab === 'insights' && (
          <div className="flex-1 overflow-hidden">
            <InsightsPanel />
          </div>
        )}
      </div>
    </div>
  );
}

interface MainTabButtonProps {
  id: MainTab;
  active: boolean;
  onClick: (id: MainTab) => void;
  children: React.ReactNode;
}

function MainTabButton({ id, active, onClick, children }: MainTabButtonProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`flex items-center px-3 py-2 text-xs font-semibold transition-colors border-b-2 ${
        active
          ? 'text-zinc-100 border-blue-400'
          : 'text-zinc-500 border-transparent hover:text-zinc-300'
      }`}
    >
      {children}
    </button>
  );
}

export default App;

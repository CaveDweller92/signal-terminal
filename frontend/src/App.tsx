import { useState } from 'react';
import { Header } from './components/layout/Header';
import { Watchlist } from './components/layout/Watchlist';
import { DetailPanel } from './components/layout/DetailPanel';
import { useSignals } from './hooks/useSignals';
import { useRegime } from './hooks/useRegime';

function App() {
  const { signals, loading, error, refresh: refreshSignals } = useSignals();
  const { regime, refresh: refreshRegime } = useRegime();
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const selectedSignal = signals.find((s) => s.symbol === selectedSymbol) ?? null;

  const handleRefresh = () => {
    refreshSignals();
    refreshRegime();
  };

  return (
    <div className="h-screen flex flex-col bg-zinc-950 text-zinc-100">
      <Header regime={regime} onRefresh={handleRefresh} loading={loading} />

      <div className="flex-1 flex overflow-hidden">
        <Watchlist
          signals={signals}
          selectedSymbol={selectedSymbol}
          onSelect={setSelectedSymbol}
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
              <div className="text-center">
                <p className="text-zinc-500 text-sm">
                  {loading
                    ? 'Loading signals...'
                    : 'Select a stock from the watchlist'}
                </p>
              </div>
            </div>
          )}

          {!error && selectedSignal && <DetailPanel signal={selectedSignal} />}
        </main>
      </div>
    </div>
  );
}

export default App;

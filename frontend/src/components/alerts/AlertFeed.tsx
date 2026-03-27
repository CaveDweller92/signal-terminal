import type { ExitSignal } from '../../types/positions';
import { AlertItem } from './AlertItem';

interface AlertFeedProps {
  alerts: ExitSignal[];
  connected: boolean;
  onClear: () => void;
}

export function AlertFeed({ alerts, connected, onClear }: AlertFeedProps) {
  return (
    <div className="flex flex-col h-full bg-zinc-950">
      {/* Feed header */}
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-600'
            }`}
          />
          <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-semibold">
            Live Alerts {connected ? '· Connected' : '· Reconnecting...'}
          </span>
        </div>
        {alerts.length > 0 && (
          <button
            onClick={onClear}
            className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Clear ({alerts.length})
          </button>
        )}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-zinc-600">
            <span className="text-2xl">📭</span>
            <p className="text-xs">No alerts yet</p>
            <p className="text-[10px] text-zinc-700">
              Exit alerts will appear here in real time
            </p>
          </div>
        ) : (
          alerts.map((alert) => <AlertItem key={alert.id} alert={alert} />)
        )}
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ExitSignal, WsMessage } from '../types/positions';
import type { Signal } from '../types/market';
import { fetchRecentAlerts } from '../services/api';
import { wsService } from '../services/websocket';

interface UseWebSocketReturn {
  connected: boolean;
  alerts: ExitSignal[];
  clearAlerts: () => void;
  onPositionUpdate: (handler: (msg: WsMessage) => void) => void;
  onSignalUpdate: (handler: (signals: Signal[]) => void) => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState<ExitSignal[]>([]);
  const positionHandlerRef = useRef<((msg: WsMessage) => void) | null>(null);
  const signalHandlerRef = useRef<((signals: Signal[]) => void) | null>(null);

  // Load existing alerts from DB on mount + poll every 30s for new ones
  useEffect(() => {
    const loadAlerts = () => {
      fetchRecentAlerts(100)
        .then((latest) => setAlerts(latest))
        .catch(() => { /* API unavailable */ });
    };
    loadAlerts();
    const alertPoll = setInterval(loadAlerts, 30_000);
    return () => clearInterval(alertPoll);
  }, []);

  useEffect(() => {
    wsService.connect();

    const poll = setInterval(() => {
      setConnected(wsService.readyState === WebSocket.OPEN);
    }, 1000);

    const unsubscribe = wsService.subscribe((msg: WsMessage) => {
      console.debug('Received WS message:', msg);
      if (msg.type === 'exit_alert' && msg.alert?.id != null) {
        setAlerts((prev) => {
          // Deduplicate by id — alert may already exist from initial fetch
          if (prev.some((a) => a.id === msg.alert.id)) return prev;
          return [msg.alert, ...prev].slice(0, 100);
        });
      } else if (msg.type === 'signal_update') {
        signalHandlerRef.current?.(msg.signals);
      }
      positionHandlerRef.current?.(msg);
    });

    return () => {
      clearInterval(poll);
      unsubscribe();
    };
  }, []);

  const clearAlerts = useCallback(() => setAlerts([]), []);

  const onPositionUpdate = useCallback((handler: (msg: WsMessage) => void) => {
    positionHandlerRef.current = handler;
  }, []);

  const onSignalUpdate = useCallback((handler: (signals: Signal[]) => void) => {
    signalHandlerRef.current = handler;
  }, []);

  return { connected, alerts, clearAlerts, onPositionUpdate, onSignalUpdate };
}

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ExitSignal, WsMessage } from '../types/positions';
import type { Signal } from '../types/market';
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

  useEffect(() => {
    wsService.connect();

    const poll = setInterval(() => {
      setConnected(wsService.readyState === WebSocket.OPEN);
    }, 1000);

    const unsubscribe = wsService.subscribe((msg: WsMessage) => {
      if (msg.type === 'exit_alert') {
        setAlerts((prev) => [msg.alert, ...prev].slice(0, 100));
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

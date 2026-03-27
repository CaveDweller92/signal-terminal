import { useState, useEffect, useCallback } from 'react';
import type { ExitSignal, WsMessage } from '../types/positions';
import { wsService } from '../services/websocket';

interface UseWebSocketReturn {
  connected: boolean;
  alerts: ExitSignal[];
  clearAlerts: () => void;
  onPositionUpdate: (handler: (msg: WsMessage) => void) => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState<ExitSignal[]>([]);
  const [positionHandler, setPositionHandler] = useState<
    ((msg: WsMessage) => void) | null
  >(null);

  useEffect(() => {
    wsService.connect();

    // Poll readyState for connection status (simple, avoids event wiring on singleton)
    const poll = setInterval(() => {
      setConnected(wsService.readyState === WebSocket.OPEN);
    }, 1000);

    const unsubscribe = wsService.subscribe((msg: WsMessage) => {
      if (msg.type === 'exit_alert') {
        setAlerts((prev) => [msg.alert, ...prev].slice(0, 100));
      }
      positionHandler?.(msg);
    });

    return () => {
      clearInterval(poll);
      unsubscribe();
    };
  }, [positionHandler]);

  const clearAlerts = useCallback(() => setAlerts([]), []);

  const onPositionUpdate = useCallback((handler: (msg: WsMessage) => void) => {
    setPositionHandler(() => handler);
  }, []);

  return { connected, alerts, clearAlerts, onPositionUpdate };
}

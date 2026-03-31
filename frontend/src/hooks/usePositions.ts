import { useState, useCallback, useEffect, useRef } from 'react';
import type { Position, TradeInput, CloseInput } from '../types/positions';
import {
  fetchOpenPositions,
  openPosition,
  closePosition,
} from '../services/api';

const POLL_INTERVAL_MS = 5 * 60_000; // 5 minutes — swing trading

function isMarketOpen(): boolean {
  const now = new Date();
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const day = et.getDay();
  if (day === 0 || day === 6) return false;
  const hours = et.getHours();
  const minutes = et.getMinutes();
  const time = hours * 60 + minutes;
  return time >= 9 * 60 + 30 && time <= 16 * 60;
}

interface UsePositionsReturn {
  positions: Position[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  addPosition: (trade: TradeInput) => Promise<void>;
  closePos: (id: number, input: CloseInput) => Promise<void>;
  updatePosition: (updated: Position) => void;
}

export function usePositions(): UsePositionsReturn {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchOpenPositions();
      setPositions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load positions');
    } finally {
      setLoading(false);
    }
  }, []);

  // Poll for updated positions every 60s — skip when market is closed
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    pollRef.current = setInterval(async () => {
      if (!isMarketOpen()) return;
      try {
        const data = await fetchOpenPositions();
        setPositions(data);
      } catch {
        // Silently ignore — next poll will retry
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const addPosition = useCallback(async (trade: TradeInput) => {
    const position = await openPosition(trade);
    setPositions((prev) => [position, ...prev]);
  }, []);

  const closePos = useCallback(async (id: number, input: CloseInput) => {
    const updated = await closePosition(id, input);
    setPositions((prev) => prev.filter((p) => p.id !== updated.id));
  }, []);

  // Called by WebSocket updates to patch live P&L without a full refresh
  const updatePosition = useCallback((updated: Position) => {
    setPositions((prev) =>
      prev.map((p) => (p.id === updated.id ? updated : p))
    );
  }, []);

  return { positions, loading, error, refresh, addPosition, closePos, updatePosition };
}

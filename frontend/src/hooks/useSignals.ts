import { useCallback, useEffect, useRef, useState } from 'react';
import type { Signal } from '../types/market';
import { fetchSignals } from '../services/api';

const POLL_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes — swing trading

function isMarketOpen(): boolean {
  const now = new Date();
  // Convert to ET (America/New_York)
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
  const day = et.getDay();
  if (day === 0 || day === 6) return false; // weekend
  const hours = et.getHours();
  const minutes = et.getMinutes();
  const time = hours * 60 + minutes;
  return time >= 9 * 60 + 30 && time <= 16 * 60; // 9:30 AM - 4:00 PM ET
}

interface UseSignalsResult {
  signals: Signal[];
  loading: boolean;
  error: string | null;
  secondsUntilRefresh: number;
  fetchedAt: string | null;
  refresh: () => void;
  applyLiveUpdate: (incoming: Signal[]) => void;
}

export function useSignals(): UseSignalsResult {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(POLL_INTERVAL_MS / 1000);
  const [fetchedAt, setFetchedAt] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const resetCountdown = useCallback(() => {
    setSecondsUntilRefresh(POLL_INTERVAL_MS / 1000);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSignals();
      setSignals(data.signals);
      setFetchedAt(data.fetched_at ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch signals');
    } finally {
      setLoading(false);
      resetCountdown();
    }
  }, [resetCountdown]);

  // Silent refresh for polling — skip when market is closed
  const poll = useCallback(async () => {
    if (!isMarketOpen()) return;
    try {
      const data = await fetchSignals();
      setSignals(data.signals);
      setFetchedAt(data.fetched_at ?? null);
    } catch {
      // Silently ignore poll failures — next poll will retry
    }
    resetCountdown();
  }, [resetCountdown]);

  useEffect(() => {
    load();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    countdownRef.current = setInterval(() => {
      setSecondsUntilRefresh((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [load, poll]);

  const refresh = useCallback(() => {
    // Reset poll timer on manual refresh
    if (intervalRef.current) clearInterval(intervalRef.current);
    load();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, [load, poll]);

  // Merge a live push: update existing symbols in-place, preserve ordering by conviction.
  const applyLiveUpdate = useCallback((incoming: Signal[]) => {
    setSignals(incoming);
  }, []);

  return { signals, loading, error, secondsUntilRefresh, fetchedAt, refresh, applyLiveUpdate };
}

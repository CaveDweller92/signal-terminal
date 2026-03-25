import { useCallback, useEffect, useState } from 'react';
import type { Signal } from '../types/market';
import { fetchSignals } from '../services/api';

interface UseSignalsResult {
  signals: Signal[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useSignals(): UseSignalsResult {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSignals();
      setSignals(data.signals);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch signals');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { signals, loading, error, refresh: load };
}

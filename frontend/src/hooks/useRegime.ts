import { useCallback, useEffect, useState } from 'react';
import type { RegimeState } from '../types/market';
import { fetchRegime } from '../services/api';

interface UseRegimeResult {
  regime: RegimeState | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useRegime(): UseRegimeResult {
  const [regime, setRegime] = useState<RegimeState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRegime();
      setRegime(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch regime');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { regime, loading, error, refresh: load };
}

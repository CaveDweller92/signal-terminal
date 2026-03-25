import type { Signal, SignalListResponse, RegimeState } from '../types/market';

const BASE_URL = '/api';

async function fetchJSON<T>(url: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function fetchSignals(symbols?: string[]): Promise<SignalListResponse> {
  const params = symbols ? `?symbols=${symbols.join(',')}` : '';
  return fetchJSON<SignalListResponse>(`/signals${params}`);
}

export function fetchSignal(symbol: string): Promise<Signal> {
  return fetchJSON<Signal>(`/signals/${symbol}`);
}

export function fetchRegime(symbol?: string): Promise<RegimeState> {
  const path = symbol ? `/regime/${symbol}` : '/regime';
  return fetchJSON<RegimeState>(path);
}

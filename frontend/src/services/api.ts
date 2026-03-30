import type { Signal, SignalListResponse, RegimeState } from '../types/market';
import type {
  Position,
  ExitSignal,
  TradeStats,
  TradeInput,
  CloseInput,
} from '../types/positions';
import type { ScreenerResponse, WatchlistResponse } from '../types/discovery';
import type {
  ParameterSnapshot,
  MetaReview,
  DailyPerformance,
  PerformanceSummary,
} from '../types/adaptation';

const BASE_URL = '/api';

async function fetchJSON<T>(url: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function putJSON<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

// --- Signals ---

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

// --- Positions ---

export function fetchOpenPositions(): Promise<Position[]> {
  return fetchJSON<Position[]>('/positions');
}

export function openPosition(trade: TradeInput): Promise<Position> {
  return postJSON<Position>('/positions', trade);
}

export function closePosition(id: number, input: CloseInput): Promise<Position> {
  return putJSON<Position>(`/positions/${id}/close`, input);
}

export function fetchPositionSignals(id: number): Promise<ExitSignal[]> {
  return fetchJSON<ExitSignal[]>(`/positions/${id}/signals`);
}

export function fetchRecentAlerts(limit = 100): Promise<ExitSignal[]> {
  return fetchJSON<ExitSignal[]>(`/positions/alerts/recent?limit=${limit}`);
}

export function fetchTradeHistory(days = 30): Promise<Position[]> {
  return fetchJSON<Position[]>(`/positions/history?days=${days}`);
}

export function fetchTradeStats(days = 30): Promise<TradeStats> {
  return fetchJSON<TradeStats>(`/positions/stats?days=${days}`);
}

// --- Discovery ---

export function fetchScreenerResults(): Promise<ScreenerResponse> {
  return fetchJSON<ScreenerResponse>('/discovery/screener');
}

export function fetchWatchlist(): Promise<WatchlistResponse> {
  return fetchJSON<WatchlistResponse>('/discovery/watchlist');
}

export function triggerScan(): Promise<unknown> {
  return postJSON<unknown>('/discovery/scan', {});
}

export function triggerWatchlistBuild(): Promise<unknown> {
  return postJSON<unknown>('/discovery/watchlist', {});
}

// --- Adaptation ---

export function fetchCurrentParameters(): Promise<ParameterSnapshot> {
  return fetchJSON<ParameterSnapshot>('/adaptation/parameters');
}

export function fetchParameterLog(limit = 50): Promise<ParameterSnapshot[]> {
  return fetchJSON<ParameterSnapshot[]>(`/adaptation/log?limit=${limit}`);
}

export function fetchMetaReviews(limit = 30): Promise<MetaReview[]> {
  return fetchJSON<MetaReview[]>(`/adaptation/reviews?limit=${limit}`);
}

export function fetchLatestMetaReview(): Promise<MetaReview | null> {
  return fetchJSON<MetaReview | null>('/adaptation/reviews/latest');
}

export function triggerMetaReview(): Promise<unknown> {
  return postJSON<unknown>('/adaptation/review', {});
}

// --- Performance ---

export function fetchDailyPerformance(days = 30): Promise<DailyPerformance[]> {
  return fetchJSON<DailyPerformance[]>(`/performance/daily?days=${days}`);
}

export function fetchPerformanceSummary(days = 30): Promise<PerformanceSummary> {
  return fetchJSON<PerformanceSummary>(`/performance/summary?days=${days}`);
}

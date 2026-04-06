/**
 * Tests for services/api.ts — URL construction and error handling.
 *
 * These ensure the frontend calls the right endpoints with the right params.
 * A wrong URL = silent data failure the user won't notice until trades go wrong.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

import {
  fetchSignals,
  fetchSignal,
  fetchRegime,
  fetchOpenPositions,
  openPosition,
  closePosition,
  fetchScreenerResults,
  fetchWatchlist,
  fetchDailyPerformance,
  fetchPerformanceSummary,
  editPosition,
  fetchTradeHistory,
  fetchTradeStats,
} from './api';

function mockOk(data: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

function mockError(status: number) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
  });
}

beforeEach(() => {
  mockFetch.mockClear();
});

describe('fetchSignals', () => {
  it('calls /api/signals with no params by default', async () => {
    mockOk({ signals: [], count: 0 });
    await fetchSignals();
    expect(mockFetch).toHaveBeenCalledWith('/api/signals');
  });

  it('passes symbols as comma-separated query param', async () => {
    mockOk({ signals: [], count: 0 });
    await fetchSignals(['AAPL', 'TSLA']);
    expect(mockFetch).toHaveBeenCalledWith('/api/signals?symbols=AAPL,TSLA');
  });
});

describe('fetchSignal', () => {
  it('calls /api/signals/:symbol', async () => {
    mockOk({ symbol: 'AAPL', signal_type: 'BUY', conviction: 1.5 });
    await fetchSignal('AAPL');
    expect(mockFetch).toHaveBeenCalledWith('/api/signals/AAPL');
  });
});

describe('fetchRegime', () => {
  it('calls /api/regime by default', async () => {
    mockOk({ regime: 'trending_up', confidence: 0.8 });
    await fetchRegime();
    expect(mockFetch).toHaveBeenCalledWith('/api/regime');
  });

  it('calls /api/regime/:symbol when provided', async () => {
    mockOk({ regime: 'trending_down', confidence: 0.7 });
    await fetchRegime('SPY');
    expect(mockFetch).toHaveBeenCalledWith('/api/regime/SPY');
  });
});

describe('position endpoints', () => {
  it('fetchOpenPositions calls /api/positions', async () => {
    mockOk([]);
    await fetchOpenPositions();
    expect(mockFetch).toHaveBeenCalledWith('/api/positions');
  });

  it('openPosition sends POST with trade data', async () => {
    mockOk({ id: 1, symbol: 'AAPL' });
    const trade = { symbol: 'AAPL', direction: 'LONG' as const, entry_price: 190, quantity: 100 };
    await openPosition(trade);
    expect(mockFetch).toHaveBeenCalledWith('/api/positions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(trade),
    });
  });

  it('closePosition sends PUT with exit data', async () => {
    mockOk({ id: 1, status: 'closed' });
    await closePosition(1, { exit_price: 200 });
    expect(mockFetch).toHaveBeenCalledWith('/api/positions/1/close', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exit_price: 200 }),
    });
  });

  it('editPosition sends PUT with updates', async () => {
    mockOk({ id: 1 });
    await editPosition(1, { entry_price: 195 });
    expect(mockFetch).toHaveBeenCalledWith('/api/positions/1/edit', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entry_price: 195 }),
    });
  });

  it('fetchTradeHistory includes days param', async () => {
    mockOk([]);
    await fetchTradeHistory(60);
    expect(mockFetch).toHaveBeenCalledWith('/api/positions/history?days=60');
  });

  it('fetchTradeStats defaults to 30 days', async () => {
    mockOk({ total_trades: 0 });
    await fetchTradeStats();
    expect(mockFetch).toHaveBeenCalledWith('/api/positions/stats?days=30');
  });
});

describe('discovery endpoints', () => {
  it('fetchScreenerResults calls /api/discovery/screener', async () => {
    mockOk({ results: [] });
    await fetchScreenerResults();
    expect(mockFetch).toHaveBeenCalledWith('/api/discovery/screener');
  });

  it('fetchWatchlist calls /api/discovery/watchlist', async () => {
    mockOk({ watchlist: [] });
    await fetchWatchlist();
    expect(mockFetch).toHaveBeenCalledWith('/api/discovery/watchlist');
  });
});

describe('performance endpoints', () => {
  it('fetchDailyPerformance includes days param', async () => {
    mockOk([]);
    await fetchDailyPerformance(90);
    expect(mockFetch).toHaveBeenCalledWith('/api/performance/daily?days=90');
  });

  it('fetchPerformanceSummary defaults to 30 days', async () => {
    mockOk({});
    await fetchPerformanceSummary();
    expect(mockFetch).toHaveBeenCalledWith('/api/performance/summary?days=30');
  });
});

describe('error handling', () => {
  it('throws on non-ok response', async () => {
    mockError(500);
    await expect(fetchSignals()).rejects.toThrow('API error: 500');
  });

  it('throws on 404', async () => {
    mockError(404);
    await expect(fetchSignal('FAKE')).rejects.toThrow('API error: 404');
  });
});

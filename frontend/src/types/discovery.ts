export interface ScreenerResult {
  id: number;
  scan_date: string;
  symbol: string;
  exchange: string | null;
  composite_score: number;
  volume_score: number | null;
  gap_score: number | null;
  technical_score: number | null;
  fundamental_score: number | null;
  news_score: number | null;
  sector_score: number | null;
  premarket_gap_pct: number | null;
  relative_volume: number | null;
  sector: string | null;
  has_catalyst: boolean;
}

export interface WatchlistEntry {
  id: number;
  watch_date: string;
  symbol: string;
  exchange: string | null;
  source: 'ai' | 'screener';
  ai_reasoning: string | null;
  screener_rank: number | null;
  sector: string | null;
  regime_at_pick: string | null;
}

export interface ScreenerResponse {
  scan_date: string;
  results: ScreenerResult[];
  count: number;
}

export interface WatchlistResponse {
  watch_date: string;
  picks: WatchlistEntry[];
  count: number;
}

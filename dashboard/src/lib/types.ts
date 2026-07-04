export type Signal = "Up" | "Down" | "Skip";

export interface MarketInfo {
  slug: string;
  question: string;
  window_start: number;
  window_end: number;
  seconds_since_start: number;
  seconds_until_close: number;
  accepting_orders: boolean;
}

export interface Stats {
  date: string;
  trades_opened: number;
  trades_settled: number;
  trades_won: number;
  trades_lost: number;
  win_rate: number | null;
  open_positions: number;
  realized_pnl_usdc: number;
}

export interface OpenPosition {
  condition_id: string;
  window_start: number;
  market_slug: string;
  token_id: string;
  outcome: "Up" | "Down";
  size_usdc: number;
  entry_price: number;
  order_id: string;
  opened_at: string;
  settled: boolean;
}

export interface TradeRecord {
  condition_id: string;
  market_slug: string;
  outcome: "Up" | "Down";
  size_usdc: number;
  entry_price: number;
  won: boolean;
  pnl_usdc: number;
  opened_at: string;
  settled_at: string;
}

export interface BotState {
  updated_at: string;
  dry_run: boolean;
  market: MarketInfo | null;
  signal: Signal | null;
  momentum_bps: number | null;
  stats: Stats;
  open_positions: OpenPosition[];
  recent_trades: TradeRecord[];
}

export type StateResponse =
  | ({ available: true } & BotState)
  | { available: false; error?: string };

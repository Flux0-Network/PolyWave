# PolyWave

A bot that trades Polymarket's **"Bitcoin Up or Down"** 5-minute markets.

Every 5 minutes Polymarket opens a new market asking whether BTC/USD will be
higher or lower at the end of the window than at the start (resolved via
Chainlink's BTC/USD stream). This bot watches short-term BTC momentum on
Binance as a proxy signal and, if the move is large enough, buys the
corresponding "Up" or "Down" outcome share.

**This is a real-money trading bot for a fast-moving prediction market. Use
at your own risk.** The default momentum strategy is a simple, unproven
example — read it, understand it, and back-test/paper-trade before risking
real funds.

## How it works

1. **Market discovery** (`polywave/gamma_client.py`) — Polymarket publishes
   these markets with deterministic slugs (`btc-updown-5m-<window_start>`),
   so the bot computes the slug for the current 5-minute window directly via
   the public Gamma API instead of scanning all markets.
2. **Price feed** (`polywave/binance_feed.py`) — pulls BTC/USDT 1-second
   klines from Binance's public REST API to measure momentum over a
   configurable lookback window. This is an approximation of the Chainlink
   feed Polymarket actually settles against, not the settlement source
   itself.
3. **Strategy** (`polywave/strategy.py`) — `MomentumStrategy` bets **Up** if
   price rose at least `MOMENTUM_THRESHOLD_BPS` over the lookback window,
   **Down** if it fell that much, otherwise skips the market as noise.
4. **Trading** (`polywave/trading_client.py`) — wraps
   [`py-clob-client`](https://github.com/Polymarket/py-clob-client) to read
   the order book and place a market (FOK) order for the chosen outcome. In
   dry-run mode no py-clob-client instance or wallet is needed at all; best
   bid/ask is read straight from the public CLOB REST API and orders are
   only logged.
5. **Risk management** (`polywave/risk.py`) — one position per market
   window, and a daily stop-loss (`MAX_DAILY_LOSS_USDC`) that halts new
   trades once hit.
6. **Loop** (`polywave/bot.py`) — polls on `POLL_INTERVAL_SECONDS`, avoids
   entering right after a window opens or right before it closes
   (`ENTRY_BUFFER_SECONDS`/`EXIT_BUFFER_SECONDS`), and settles past
   positions once Polymarket resolves them.

## Trade stats

The bot logs a summary line (`Stats <date>: opened=... settled=... won=...
lost=... win_rate=... open=... pnl=...`) after every settled trade and every
`STATS_LOG_INTERVAL_SECONDS` (default 15 min), so you can see trade
frequency, win rate, and simulated/real PnL without digging through every
line. Stats (and the daily loss limit) automatically reset at UTC midnight.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

By default `DRY_RUN=true` — the bot logs what it *would* do (market picked,
signal, order, simulated PnL) without ever placing a real order or needing a
wallet. Run it and watch the logs before doing anything else:

```bash
python main.py
```

## Going live

**Only after you've reviewed the strategy and are comfortable with the
risk.**

1. Get a Polygon wallet funded with USDC and (a small amount of) MATIC/POL
   for gas, and note its private key.
2. In `.env`, set:
   ```
   DRY_RUN=false
   POLYMARKET_PRIVATE_KEY=0x...
   ```
   API credentials (`POLYMARKET_API_KEY`/`_SECRET`/`_PASSPHRASE`) are
   optional — if omitted, the bot derives them from your private key on
   startup via `create_or_derive_api_creds`.
3. Start with a small `TRADE_SIZE_USDC` and a conservative
   `MAX_DAILY_LOSS_USDC`.
4. Never commit your `.env` file or private key.

## Configuration

See `.env.example` for the full list of environment variables (strategy
thresholds, timing buffers, trade size, daily loss limit, API endpoints).

## Dashboard

`dashboard/` is a Next.js app that shows the bot's live state: the current
market and countdown, today's stats (PnL, win rate, trades, open positions),
a cumulative PnL chart, and a recent-trades table. It polls a JSON snapshot
the bot writes to `data/state.json` (`STATE_FILE_PATH`) on every tick — no
database, no extra process to run on the Python side.

```bash
# terminal 1: the bot (writes data/state.json as it runs)
python main.py

# terminal 2: the dashboard
cd dashboard
npm install
npm run dev
```

Open http://localhost:3000. If no state file exists yet (bot not started,
or a different `STATE_FILE_PATH`), the dashboard shows an empty state and
starts polling automatically once one appears.

The dashboard only reads the state file — it never talks to Polymarket,
Binance, or your wallet directly, so it's safe to leave open even in live
mode.

### Deploying the dashboard to Vercel

The bot has to keep running somewhere with a persistent process (a VPS, your
own machine, etc.) — Vercel only runs the *dashboard*. Since Vercel functions
can't read that machine's local `data/state.json`, the bot instead pushes the
same snapshot to a small REST-based key/value store that both sides can
reach over HTTPS:

1. **Create a KV store.** Easiest: in the Vercel dashboard, add the
   "Upstash for Redis" integration (Storage tab) to your project — it
   provisions a free Redis DB and gives you a REST URL + token. (A standalone
   [Upstash](https://upstash.com) account works identically.)
2. **Configure the bot.** In the bot's `.env`, set `KV_REST_API_URL` and
   `KV_REST_API_TOKEN` to those values. The bot now pushes its state
   snapshot there on every tick, in addition to the local file.
3. **Import the repo into Vercel.** New Project → this repo → set
   **Root Directory** to `dashboard` (it's a subfolder, not the repo root).
4. **Add the same two env vars** (`KV_REST_API_URL`, `KV_REST_API_TOKEN`) to
   the Vercel project's Environment Variables — if you used the Upstash
   integration in step 1, Vercel already injected them for you.
5. **Deploy.** As long as the bot is running somewhere and pushing, the
   deployed dashboard shows live state. If the bot stops for more than
   `STATE_TTL_SECONDS` (default 120s), the snapshot expires and the
   dashboard falls back to its empty state rather than showing stale data.

Local development is unaffected — without those two env vars set, both the
bot and the dashboard fall back to the local `data/state.json` file, no KV
store needed.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests cover the strategy, risk/PnL, market-slug parsing, and momentum
calculation using mocked HTTP responses — no network access or live
credentials required.

## Known limitations

- Binance's public API is geo-restricted in some jurisdictions; if
  `BinancePriceFeed` requests fail there, swap in another BTC/USDT spot feed.
- The momentum strategy is intentionally simple and included as a working
  example/baseline, not a proven edge.
- The bot holds one open position per market window; it does not hedge,
  average down, or trade multiple markets concurrently.

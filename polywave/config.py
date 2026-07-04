"""Runtime configuration loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


@dataclass(frozen=True)
class Config:
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", True))

    polymarket_private_key: str | None = field(
        default_factory=lambda: os.getenv("POLYMARKET_PRIVATE_KEY") or None
    )
    polymarket_host: str = field(
        default_factory=lambda: os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
    )
    polymarket_chain_id: int = field(default_factory=lambda: _int("POLYMARKET_CHAIN_ID", 137))
    polymarket_api_key: str | None = field(default_factory=lambda: os.getenv("POLYMARKET_API_KEY") or None)
    polymarket_api_secret: str | None = field(default_factory=lambda: os.getenv("POLYMARKET_API_SECRET") or None)
    polymarket_api_passphrase: str | None = field(
        default_factory=lambda: os.getenv("POLYMARKET_API_PASSPHRASE") or None
    )

    gamma_api_url: str = field(
        default_factory=lambda: os.getenv("GAMMA_API_URL", "https://gamma-api.polymarket.com")
    )

    binance_api_url: str = field(default_factory=lambda: os.getenv("BINANCE_API_URL", "https://api.binance.com"))
    btc_symbol: str = field(default_factory=lambda: os.getenv("BTC_SYMBOL", "BTCUSDT"))

    momentum_lookback_seconds: int = field(default_factory=lambda: _int("MOMENTUM_LOOKBACK_SECONDS", 60))
    momentum_threshold_bps: float = field(default_factory=lambda: _float("MOMENTUM_THRESHOLD_BPS", 15))

    entry_buffer_seconds: int = field(default_factory=lambda: _int("ENTRY_BUFFER_SECONDS", 30))
    exit_buffer_seconds: int = field(default_factory=lambda: _int("EXIT_BUFFER_SECONDS", 20))
    poll_interval_seconds: int = field(default_factory=lambda: _int("POLL_INTERVAL_SECONDS", 5))
    stats_log_interval_seconds: int = field(default_factory=lambda: _int("STATS_LOG_INTERVAL_SECONDS", 900))

    state_file_path: str = field(default_factory=lambda: os.getenv("STATE_FILE_PATH", "data/state.json"))
    # Optional: push the same state snapshot to an Upstash/Vercel KV REST
    # endpoint so a dashboard deployed on Vercel (which can't read this
    # machine's filesystem) can read it too. Both env var names are the ones
    # Vercel's Upstash-backed KV integration injects automatically.
    kv_rest_api_url: str | None = field(default_factory=lambda: os.getenv("KV_REST_API_URL") or None)
    kv_rest_api_token: str | None = field(default_factory=lambda: os.getenv("KV_REST_API_TOKEN") or None)
    state_ttl_seconds: int = field(default_factory=lambda: _int("STATE_TTL_SECONDS", 120))

    trade_size_usdc: float = field(default_factory=lambda: _float("TRADE_SIZE_USDC", 5))
    max_daily_loss_usdc: float = field(default_factory=lambda: _float("MAX_DAILY_LOSS_USDC", 50))

    def require_live_credentials(self) -> None:
        if not self.dry_run and not self.polymarket_private_key:
            raise ValueError(
                "DRY_RUN is false but POLYMARKET_PRIVATE_KEY is not set. "
                "Set it in your .env or keep DRY_RUN=true."
            )

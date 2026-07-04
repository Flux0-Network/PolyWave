"""BTC/USDT spot price feed used as the momentum signal input.

Polymarket's "Bitcoin Up or Down" markets resolve against Chainlink's BTC/USD
stream, not Binance. Binance is used here purely as a fast, free, public proxy
for short-term BTC momentum -- it tracks Chainlink's feed closely enough for a
directional signal, but this is an approximation, not the settlement source.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from polywave.config import Config


@dataclass(frozen=True)
class PricePoint:
    timestamp: float
    price: float


class BinancePriceFeed:
    def __init__(self, config: Config, session: requests.Session | None = None):
        self._config = config
        self._session = session or requests.Session()

    def get_price(self) -> float:
        resp = self._session.get(
            f"{self._config.binance_api_url}/api/v3/ticker/price",
            params={"symbol": self._config.btc_symbol},
            timeout=10,
        )
        resp.raise_for_status()
        return float(resp.json()["price"])

    def get_recent_prices(self, lookback_seconds: int) -> list[PricePoint]:
        """Return roughly one price sample per second for the lookback window."""
        limit = max(2, min(lookback_seconds, 1000))
        resp = self._session.get(
            f"{self._config.binance_api_url}/api/v3/klines",
            params={
                "symbol": self._config.btc_symbol,
                "interval": "1s",
                "limit": limit,
            },
            timeout=10,
        )
        resp.raise_for_status()
        klines = resp.json()
        return [PricePoint(timestamp=k[0] / 1000, price=float(k[4])) for k in klines]

    def get_momentum_bps(self, lookback_seconds: int) -> float:
        """Percent change over the lookback window, expressed in basis points."""
        prices = self.get_recent_prices(lookback_seconds)
        if len(prices) < 2:
            return 0.0
        start, end = prices[0].price, prices[-1].price
        if start == 0:
            return 0.0
        return (end - start) / start * 10_000

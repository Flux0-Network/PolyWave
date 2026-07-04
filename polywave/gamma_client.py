"""Discovers the currently tradeable Polymarket "Bitcoin Up or Down" 5-minute
market via the public Gamma API (https://gamma-api.polymarket.com).

Polymarket runs these as a back-to-back series of markets, one per 5-minute
UTC-aligned window, with slugs of the form ``btc-updown-5m-<window_start_unix>``
where ``window_start_unix`` is a multiple of 300. This lets us compute the slug
for "now" directly instead of paging through the full market list.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass

import requests

from polywave.config import Config

WINDOW_SECONDS = 300
SLUG_PREFIX = "btc-updown-5m"


@dataclass(frozen=True)
class Market:
    condition_id: str
    slug: str
    question: str
    window_start: int
    window_end: int
    outcomes: list[str]
    token_ids: list[str]
    outcome_prices: list[float]
    accepting_orders: bool
    closed: bool

    @property
    def seconds_since_start(self) -> float:
        return time.time() - self.window_start

    @property
    def seconds_until_close(self) -> float:
        return self.window_end - time.time()

    def token_id_for(self, outcome: str) -> str:
        try:
            index = [o.lower() for o in self.outcomes].index(outcome.lower())
        except ValueError as exc:
            raise ValueError(f"Unknown outcome {outcome!r}; expected one of {self.outcomes}") from exc
        return self.token_ids[index]

    def winning_outcome(self) -> str | None:
        """Return the winning outcome name once the market has resolved."""
        if not self.closed or not self.outcome_prices:
            return None
        best_index = max(range(len(self.outcome_prices)), key=lambda i: self.outcome_prices[i])
        if self.outcome_prices[best_index] < 0.99:
            return None
        return self.outcomes[best_index]


def _window_start(ts: float) -> int:
    return int(ts - (ts % WINDOW_SECONDS))


def _parse_market(raw: dict) -> Market:
    return Market(
        condition_id=raw["conditionId"],
        slug=raw["slug"],
        question=raw["question"],
        window_start=int(raw["_window_start"]),
        window_end=int(raw["_window_start"]) + WINDOW_SECONDS,
        outcomes=json.loads(raw["outcomes"]),
        token_ids=json.loads(raw["clobTokenIds"]),
        outcome_prices=[float(p) for p in json.loads(raw.get("outcomePrices", "[]"))],
        accepting_orders=bool(raw.get("acceptingOrders", False)),
        closed=bool(raw.get("closed", False)),
    )


class GammaClient:
    def __init__(self, config: Config, session: requests.Session | None = None):
        self._config = config
        self._session = session or requests.Session()

    def _fetch_by_slug(self, slug: str) -> dict | None:
        resp = self._session.get(
            f"{self._config.gamma_api_url}/markets",
            params={"slug": slug},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        return results[0] if results else None

    def get_market_for_window(self, window_start: int) -> Market | None:
        slug = f"{SLUG_PREFIX}-{window_start}"
        raw = self._fetch_by_slug(slug)
        if raw is None:
            return None
        raw["_window_start"] = window_start
        return _parse_market(raw)

    def get_current_market(self) -> Market | None:
        """Return the market for the 5-minute window containing "now".

        Falls back to the next window if the current one isn't published yet
        (e.g. right at a window boundary), and to the previous window if the
        current one hasn't been created a few seconds into it.
        """
        now = time.time()
        start = _window_start(now)
        for candidate_start in (start, start + WINDOW_SECONDS, start - WINDOW_SECONDS):
            market = self.get_market_for_window(candidate_start)
            if market and not market.closed and market.window_start <= now < market.window_end:
                return market
        return None

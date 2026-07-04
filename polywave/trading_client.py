"""Thin wrapper around py-clob-client for reading order books and placing
market orders on Polymarket's CLOB, with a dry-run mode that never touches
the network for order placement.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from polywave.config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    token_id: str
    side: str
    size_usdc: float
    price: float
    dry_run: bool


class TradingClient:
    """Live orders require py-clob-client and a funded Polygon wallet.

    In dry-run mode (the default), no py-clob-client instance is created and
    no HTTP requests are made for trading -- best bid/ask is read from the
    public CLOB REST API directly so the bot can still simulate fills.
    """

    def __init__(self, config: Config):
        self._config = config
        self._client = None
        if not config.dry_run:
            self._client = self._build_live_client()

    def _build_live_client(self):
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds

        self._config.require_live_credentials()
        creds = None
        if self._config.polymarket_api_key:
            creds = ApiCreds(
                api_key=self._config.polymarket_api_key,
                api_secret=self._config.polymarket_api_secret,
                api_passphrase=self._config.polymarket_api_passphrase,
            )
        client = ClobClient(
            self._config.polymarket_host,
            chain_id=self._config.polymarket_chain_id,
            key=self._config.polymarket_private_key,
            creds=creds,
        )
        if creds is None:
            derived = client.create_or_derive_api_creds()
            client.set_api_creds(derived)
        return client

    def get_best_price(self, token_id: str, side: str) -> float:
        """Best price to take liquidity: best ask to BUY, best bid to SELL."""
        book = self._get_order_book(token_id)
        levels = book.asks if side == "BUY" else book.bids
        if not levels:
            raise RuntimeError(f"No {'asks' if side == 'BUY' else 'bids'} in order book for {token_id}")
        # asks/bids are typically returned worst-to-best; the best price is
        # the lowest ask / highest bid.
        prices = [float(level.price) for level in levels]
        return min(prices) if side == "BUY" else max(prices)

    def _get_order_book(self, token_id: str):
        if self._client is not None:
            return self._client.get_order_book(token_id)
        import requests

        resp = requests.get(
            f"{self._config.polymarket_host}/book",
            params={"token_id": token_id},
            timeout=10,
        )
        resp.raise_for_status()
        return _RestOrderBook(resp.json())

    def place_market_order(self, token_id: str, side: str, size_usdc: float) -> OrderResult:
        price = self.get_best_price(token_id, side)

        if self._client is None:
            order_id = f"dryrun-{uuid.uuid4()}"
            logger.info(
                "[DRY RUN] would place %s order for %s USDC on token %s at ~%.4f (order_id=%s)",
                side,
                size_usdc,
                token_id,
                price,
                order_id,
            )
            return OrderResult(
                order_id=order_id,
                token_id=token_id,
                side=side,
                size_usdc=size_usdc,
                price=price,
                dry_run=True,
            )

        from py_clob_client.clob_types import MarketOrderArgs, OrderType

        order_args = MarketOrderArgs(token_id=token_id, amount=size_usdc, side=side)
        signed_order = self._client.create_market_order(order_args)
        response = self._client.post_order(signed_order, orderType=OrderType.FOK)
        order_id = response.get("orderID") or response.get("orderId") or str(response)
        logger.info("Placed live %s order for %s USDC on token %s: %s", side, size_usdc, token_id, response)
        return OrderResult(
            order_id=order_id,
            token_id=token_id,
            side=side,
            size_usdc=size_usdc,
            price=price,
            dry_run=False,
        )


class _RestOrderBook:
    """Adapts the raw /book REST response to look like OrderBookSummary."""

    def __init__(self, raw: dict):
        self.bids = [_Level(level) for level in raw.get("bids", [])]
        self.asks = [_Level(level) for level in raw.get("asks", [])]


class _Level:
    def __init__(self, raw: dict):
        self.price = raw["price"]
        self.size = raw["size"]

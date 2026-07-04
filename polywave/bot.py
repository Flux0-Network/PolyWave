"""Main orchestration loop: watch the current 5-minute BTC market, decide,
trade once per window, and settle past positions once they resolve.
"""
from __future__ import annotations

import logging
import time

from polywave.binance_feed import BinancePriceFeed
from polywave.config import Config
from polywave.gamma_client import GammaClient, Market
from polywave.risk import Position, RiskManager
from polywave.strategy import MomentumStrategy, Signal
from polywave.trading_client import TradingClient

logger = logging.getLogger(__name__)


class Bot:
    def __init__(self, config: Config):
        self.config = config
        self.price_feed = BinancePriceFeed(config)
        self.gamma = GammaClient(config)
        self.trading = TradingClient(config)
        self.strategy = MomentumStrategy(threshold_bps=config.momentum_threshold_bps)
        self.risk = RiskManager(config=config)

    def run_forever(self) -> None:
        logger.info("Starting PolyWave (dry_run=%s)", self.config.dry_run)
        while True:
            try:
                self.tick()
            except Exception:
                logger.exception("Unhandled error during tick; continuing.")
            time.sleep(self.config.poll_interval_seconds)

    def tick(self) -> None:
        self._settle_pending_positions()

        market = self.gamma.get_current_market()
        if market is None:
            logger.warning("No active BTC 5-minute market found; will retry.")
            return

        if not self._within_entry_window(market):
            return

        if not self.risk.can_open_new_trade(market.condition_id):
            return

        if not market.accepting_orders:
            logger.debug("Market %s not accepting orders yet.", market.slug)
            return

        momentum_bps = self.price_feed.get_momentum_bps(self.config.momentum_lookback_seconds)
        signal = self.strategy.decide(momentum_bps)
        logger.info("%s momentum=%.2fbps -> signal=%s", market.slug, momentum_bps, signal.value)

        if signal is Signal.SKIP:
            return

        self._open_position(market, signal)

    def _within_entry_window(self, market: Market) -> bool:
        if market.seconds_since_start < self.config.entry_buffer_seconds:
            return False
        if market.seconds_until_close < self.config.exit_buffer_seconds:
            return False
        return True

    def _open_position(self, market: Market, signal: Signal) -> None:
        token_id = market.token_id_for(signal.value)
        result = self.trading.place_market_order(token_id, "BUY", self.config.trade_size_usdc)
        self.risk.record_open(
            Position(
                condition_id=market.condition_id,
                window_start=market.window_start,
                token_id=token_id,
                outcome=signal.value,
                size_usdc=result.size_usdc,
                entry_price=result.price,
                order_id=result.order_id,
            )
        )
        logger.info(
            "Opened %s position in %s: %.2f USDC @ %.4f (order_id=%s, dry_run=%s)",
            signal.value,
            market.slug,
            result.size_usdc,
            result.price,
            result.order_id,
            result.dry_run,
        )

    def _settle_pending_positions(self) -> None:
        for position in list(self.risk.positions.values()):
            if position.settled:
                continue
            market = self.gamma.get_market_for_window(position.window_start)
            if market is None:
                continue
            winner = market.winning_outcome()
            if winner is None:
                continue
            self.risk.settle(position.condition_id, won=winner.lower() == position.outcome.lower())

"""Position tracking and simple daily-loss risk limits.

Each 5-minute market can only be traded once. Realized PnL is settled once a
market resolves (its winning outcome becomes known) and is used to enforce a
daily stop-loss.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from polywave.config import Config

logger = logging.getLogger(__name__)


@dataclass
class Position:
    condition_id: str
    window_start: int
    token_id: str
    outcome: str
    size_usdc: float
    entry_price: float
    order_id: str
    settled: bool = False


@dataclass
class RiskManager:
    config: Config
    realized_pnl_usdc: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)

    def can_open_new_trade(self, condition_id: str) -> bool:
        if condition_id in self.positions:
            return False
        if self.realized_pnl_usdc <= -abs(self.config.max_daily_loss_usdc):
            logger.warning(
                "Daily loss limit reached (%.2f USDC); refusing new trades until reset.",
                self.realized_pnl_usdc,
            )
            return False
        return True

    def record_open(self, position: Position) -> None:
        self.positions[position.condition_id] = position

    def settle(self, condition_id: str, won: bool) -> float | None:
        """Record the outcome of a resolved market and return its PnL."""
        position = self.positions.get(condition_id)
        if position is None or position.settled:
            return None
        shares = position.size_usdc / position.entry_price
        payout = shares if won else 0.0
        pnl = payout - position.size_usdc
        position.settled = True
        self.realized_pnl_usdc += pnl
        logger.info(
            "Settled %s (%s): %s, pnl=%.4f USDC, running total=%.4f USDC",
            condition_id,
            position.outcome,
            "WON" if won else "LOST",
            pnl,
            self.realized_pnl_usdc,
        )
        return pnl

    def reset_daily(self) -> None:
        self.realized_pnl_usdc = 0.0
        self.positions = {k: v for k, v in self.positions.items() if not v.settled}

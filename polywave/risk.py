"""Position tracking, trade statistics, and a daily-loss risk limit.

Each 5-minute market can only be traded once. Realized PnL is settled once a
market resolves (its winning outcome becomes known) and is used to enforce a
daily stop-loss. Stats (trade count, win rate, PnL) reset at UTC midnight.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from polywave.config import Config

logger = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


HISTORY_LIMIT = 200


@dataclass
class Position:
    condition_id: str
    window_start: int
    market_slug: str
    token_id: str
    outcome: str
    size_usdc: float
    entry_price: float
    order_id: str
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    settled: bool = False


@dataclass
class RiskManager:
    config: Config
    realized_pnl_usdc: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    trades_opened: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    stats_date: str = field(default_factory=_today)
    history: list[dict] = field(default_factory=list)

    def can_open_new_trade(self, condition_id: str) -> bool:
        self.roll_day_if_needed()
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
        self.trades_opened += 1

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
        if won:
            self.trades_won += 1
        else:
            self.trades_lost += 1
        self.history.append(
            {
                "condition_id": position.condition_id,
                "market_slug": position.market_slug,
                "outcome": position.outcome,
                "size_usdc": position.size_usdc,
                "entry_price": position.entry_price,
                "won": won,
                "pnl_usdc": pnl,
                "opened_at": position.opened_at,
                "settled_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        del self.history[:-HISTORY_LIMIT]
        logger.info(
            "Settled %s (%s): %s, pnl=%.4f USDC, running total=%.4f USDC",
            condition_id,
            position.outcome,
            "WON" if won else "LOST",
            pnl,
            self.realized_pnl_usdc,
        )
        return pnl

    def summary(self) -> dict:
        settled = self.trades_won + self.trades_lost
        win_rate = self.trades_won / settled if settled else None
        return {
            "date": self.stats_date,
            "trades_opened": self.trades_opened,
            "trades_settled": settled,
            "trades_won": self.trades_won,
            "trades_lost": self.trades_lost,
            "win_rate": win_rate,
            "open_positions": sum(1 for p in self.positions.values() if not p.settled),
            "realized_pnl_usdc": self.realized_pnl_usdc,
        }

    def log_summary(self) -> None:
        stats = self.summary()
        win_rate = f"{stats['win_rate']:.0%}" if stats["win_rate"] is not None else "n/a"
        logger.info(
            "Stats %s: opened=%d settled=%d won=%d lost=%d win_rate=%s open=%d pnl=%.2f USDC",
            stats["date"],
            stats["trades_opened"],
            stats["trades_settled"],
            stats["trades_won"],
            stats["trades_lost"],
            win_rate,
            stats["open_positions"],
            stats["realized_pnl_usdc"],
        )

    def roll_day_if_needed(self) -> None:
        today = _today()
        if today == self.stats_date:
            return
        self.log_summary()
        self.reset_daily()
        self.stats_date = today

    def reset_daily(self) -> None:
        self.realized_pnl_usdc = 0.0
        self.trades_opened = 0
        self.trades_won = 0
        self.trades_lost = 0
        self.positions = {k: v for k, v in self.positions.items() if not v.settled}

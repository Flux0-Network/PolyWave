"""Trading signal generation.

The bot is built around a pluggable `Strategy` so the momentum default can be
swapped out without touching the bot loop.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class Signal(enum.Enum):
    UP = "Up"
    DOWN = "Down"
    SKIP = "Skip"


@dataclass(frozen=True)
class MomentumStrategy:
    """Bets that BTC keeps moving in the direction of its recent trend.

    If the price moved up by at least `threshold_bps` over the lookback
    window, bet Up; if it moved down by at least that much, bet Down.
    Anything smaller is treated as noise and skipped.
    """

    threshold_bps: float

    def decide(self, momentum_bps: float) -> Signal:
        if momentum_bps >= self.threshold_bps:
            return Signal.UP
        if momentum_bps <= -self.threshold_bps:
            return Signal.DOWN
        return Signal.SKIP

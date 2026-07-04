#!/usr/bin/env python3
"""Entrypoint for the PolyWave BTC 5-minute Polymarket bot.

Usage:
    python main.py

Configuration is read from environment variables / a .env file -- see
.env.example. The bot starts in DRY_RUN mode (no real orders) unless
DRY_RUN=false is set explicitly.
"""
from __future__ import annotations

import logging
import sys

from polywave.bot import Bot
from polywave.config import Config


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = Config()
    try:
        config.require_live_credentials()
    except ValueError as exc:
        logging.getLogger(__name__).error(str(exc))
        return 1

    bot = Bot(config)
    try:
        bot.run_forever()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down.")
        bot.risk.log_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())

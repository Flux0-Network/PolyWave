"""Writes a JSON snapshot of the bot's state for the dashboard to read.

The local file write is atomic (write to a temp file, then rename) so the
dashboard never reads a half-written file. If KV_REST_API_URL/TOKEN are set,
the same snapshot is also pushed to an Upstash-compatible REST KV store --
this is what lets a dashboard deployed on Vercel (which cannot read this
machine's filesystem) see live state. Both are independent; the local file
write always happens, the KV push is best-effort and never raises.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from polywave.config import Config
from polywave.gamma_client import Market
from polywave.risk import RiskManager
from polywave.strategy import Signal

logger = logging.getLogger(__name__)

# Must match the key the dashboard's /api/state route reads.
KV_STATE_KEY = "polywave:state"


class StateStore:
    def __init__(self, config: Config):
        self._path = Path(config.state_file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        config: Config,
        risk: RiskManager,
        market: Market | None = None,
        signal: Signal | None = None,
        momentum_bps: float | None = None,
    ) -> None:
        snapshot: dict[str, Any] = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": config.dry_run,
            "market": _market_payload(market),
            "signal": signal.value if signal else None,
            "momentum_bps": momentum_bps,
            "stats": risk.summary(),
            "open_positions": [asdict(p) for p in risk.positions.values() if not p.settled],
            "recent_trades": list(reversed(risk.history[-50:])),
        }
        payload = json.dumps(snapshot, indent=2)

        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(payload)
        tmp_path.replace(self._path)

        self._push_to_kv(config, payload)

    def _push_to_kv(self, config: Config, payload: str) -> None:
        if not (config.kv_rest_api_url and config.kv_rest_api_token):
            return
        try:
            requests.post(
                f"{config.kv_rest_api_url}/set/{KV_STATE_KEY}",
                params={"EX": config.state_ttl_seconds},
                data=payload,
                headers={"Authorization": f"Bearer {config.kv_rest_api_token}"},
                timeout=10,
            ).raise_for_status()
        except requests.RequestException:
            logger.warning("Failed to push state to remote KV store", exc_info=True)


def _market_payload(market: Market | None) -> dict | None:
    if market is None:
        return None
    return {
        "slug": market.slug,
        "question": market.question,
        "window_start": market.window_start,
        "window_end": market.window_end,
        "seconds_since_start": market.seconds_since_start,
        "seconds_until_close": market.seconds_until_close,
        "accepting_orders": market.accepting_orders,
    }

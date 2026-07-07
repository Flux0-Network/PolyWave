"""Writes a JSON snapshot of the bot's state for the dashboard to read.

The local file write is atomic (write to a temp file, then rename) so the
dashboard never reads a half-written file. If SUPABASE_URL/SERVICE_ROLE_KEY
are set, the same snapshot is also upserted into a Supabase table -- this is
what lets a dashboard deployed on Vercel (which cannot read this machine's
filesystem) see live state. Both are independent; the local file write
always happens, the Supabase push is best-effort and never raises.
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

# Must match the row id the dashboard's /api/state route reads.
SUPABASE_STATE_ROW_ID = "singleton"
SUPABASE_TABLE = "bot_state"


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
        updated_at = datetime.now(timezone.utc).isoformat()
        snapshot: dict[str, Any] = {
            "updated_at": updated_at,
            "dry_run": config.dry_run,
            "market": _market_payload(market),
            "signal": signal.value if signal else None,
            "momentum_bps": momentum_bps,
            "stats": risk.summary(),
            "open_positions": [asdict(p) for p in risk.positions.values() if not p.settled],
            "recent_trades": list(reversed(risk.history[-50:])),
        }

        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(snapshot, indent=2))
        tmp_path.replace(self._path)

        self._push_to_supabase(config, snapshot, updated_at)

    def _push_to_supabase(self, config: Config, snapshot: dict[str, Any], updated_at: str) -> None:
        if not (config.supabase_url and config.supabase_service_role_key):
            return
        try:
            requests.post(
                f"{config.supabase_url}/rest/v1/{SUPABASE_TABLE}",
                params={"on_conflict": "id"},
                json=[{"id": SUPABASE_STATE_ROW_ID, "data": snapshot, "updated_at": updated_at}],
                headers={
                    "apikey": config.supabase_service_role_key,
                    "Authorization": f"Bearer {config.supabase_service_role_key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                },
                timeout=10,
            ).raise_for_status()
        except requests.RequestException:
            logger.warning("Failed to push state to Supabase", exc_info=True)


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

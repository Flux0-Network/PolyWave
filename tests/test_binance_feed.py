from unittest.mock import MagicMock

from polywave.binance_feed import BinancePriceFeed
from polywave.config import Config


def klines_response(closes):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [
        [i * 1000, "0", "0", "0", str(close), "0"] for i, close in enumerate(closes)
    ]
    return resp


def test_momentum_bps_positive_move():
    session = MagicMock()
    session.get.return_value = klines_response([100.0, 100.5, 101.0])
    feed = BinancePriceFeed(Config(dry_run=True), session=session)

    momentum = feed.get_momentum_bps(lookback_seconds=3)

    assert momentum == (101.0 - 100.0) / 100.0 * 10_000


def test_momentum_bps_zero_with_single_sample():
    session = MagicMock()
    session.get.return_value = klines_response([100.0])
    feed = BinancePriceFeed(Config(dry_run=True), session=session)

    assert feed.get_momentum_bps(lookback_seconds=3) == 0.0

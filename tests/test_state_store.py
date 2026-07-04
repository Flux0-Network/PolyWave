import json
from unittest.mock import patch

from polywave.config import Config
from polywave.gamma_client import Market
from polywave.risk import Position, RiskManager
from polywave.state_store import KV_STATE_KEY, StateStore
from polywave.strategy import Signal


def make_market(window_start=1_700_000_000):
    return Market(
        condition_id="0xabc",
        slug=f"btc-updown-5m-{window_start}",
        question="Bitcoin Up or Down",
        window_start=window_start,
        window_end=window_start + 300,
        outcomes=["Up", "Down"],
        token_ids=["111", "222"],
        outcome_prices=[],
        accepting_orders=True,
        closed=False,
    )


def test_write_creates_parent_dir_and_valid_json(tmp_path):
    state_path = tmp_path / "nested" / "state.json"
    config = Config(dry_run=True, state_file_path=str(state_path))
    risk = RiskManager(config=config)
    store = StateStore(config)

    store.write(config, risk, market=make_market(), signal=Signal.UP, momentum_bps=25.0)

    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data["dry_run"] is True
    assert data["market"]["slug"] == "btc-updown-5m-1700000000"
    assert data["signal"] == "Up"
    assert data["momentum_bps"] == 25.0
    assert data["stats"]["trades_opened"] == 0


def test_write_with_no_market_sets_null(tmp_path):
    state_path = tmp_path / "state.json"
    config = Config(dry_run=True, state_file_path=str(state_path))
    risk = RiskManager(config=config)
    store = StateStore(config)

    store.write(config, risk)

    data = json.loads(state_path.read_text())
    assert data["market"] is None
    assert data["signal"] is None


def test_write_includes_open_positions_and_recent_trades(tmp_path):
    state_path = tmp_path / "state.json"
    config = Config(dry_run=True, state_file_path=str(state_path))
    risk = RiskManager(config=config)
    risk.record_open(
        Position(
            condition_id="c1",
            window_start=1_700_000_000,
            market_slug="btc-updown-5m-1700000000",
            token_id="111",
            outcome="Up",
            size_usdc=5,
            entry_price=0.5,
            order_id="order-1",
        )
    )
    store = StateStore(config)
    store.write(config, risk)

    data = json.loads(state_path.read_text())
    assert len(data["open_positions"]) == 1
    assert data["open_positions"][0]["condition_id"] == "c1"

    risk.settle("c1", won=True)
    store.write(config, risk)
    data = json.loads(state_path.read_text())
    assert data["open_positions"] == []
    assert len(data["recent_trades"]) == 1
    assert data["recent_trades"][0]["won"] is True


def test_write_skips_kv_push_when_not_configured(tmp_path):
    config = Config(dry_run=True, state_file_path=str(tmp_path / "state.json"))
    risk = RiskManager(config=config)
    store = StateStore(config)

    with patch("polywave.state_store.requests.post") as mock_post:
        store.write(config, risk)

    mock_post.assert_not_called()


def test_write_pushes_to_kv_when_configured(tmp_path):
    config = Config(
        dry_run=True,
        state_file_path=str(tmp_path / "state.json"),
        kv_rest_api_url="https://example-kv.upstash.io",
        kv_rest_api_token="secret-token",
        state_ttl_seconds=60,
    )
    risk = RiskManager(config=config)
    store = StateStore(config)

    with patch("polywave.state_store.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        store.write(config, risk, signal=Signal.DOWN, momentum_bps=-20.0)

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == f"https://example-kv.upstash.io/set/{KV_STATE_KEY}"
    assert kwargs["params"] == {"EX": 60}
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    body = json.loads(kwargs["data"])
    assert body["signal"] == "Down"
    assert body["momentum_bps"] == -20.0


def test_write_swallows_kv_push_errors(tmp_path):
    import requests

    state_path = tmp_path / "state.json"
    config = Config(
        dry_run=True,
        state_file_path=str(state_path),
        kv_rest_api_url="https://example-kv.upstash.io",
        kv_rest_api_token="secret-token",
    )
    risk = RiskManager(config=config)
    store = StateStore(config)

    with patch("polywave.state_store.requests.post", side_effect=requests.ConnectionError("boom")):
        store.write(config, risk)  # must not raise

    assert state_path.exists()  # local file write still happened

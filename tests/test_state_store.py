import json

from polywave.config import Config
from polywave.gamma_client import Market
from polywave.risk import Position, RiskManager
from polywave.state_store import StateStore
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

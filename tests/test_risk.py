from polywave.config import Config
from polywave.risk import Position, RiskManager


def make_position(condition_id="c1", window_start=0, outcome="Up", size_usdc=5, entry_price=0.5):
    return Position(
        condition_id=condition_id,
        window_start=window_start,
        token_id="token",
        outcome=outcome,
        size_usdc=size_usdc,
        entry_price=entry_price,
        order_id="order-1",
    )


def test_cannot_open_two_positions_in_the_same_market():
    risk = RiskManager(config=Config(dry_run=True))
    risk.record_open(make_position(condition_id="c1"))
    assert risk.can_open_new_trade("c1") is False
    assert risk.can_open_new_trade("c2") is True


def test_settle_win_computes_positive_pnl():
    risk = RiskManager(config=Config(dry_run=True))
    risk.record_open(make_position(size_usdc=5, entry_price=0.5))
    pnl = risk.settle("c1", won=True)
    assert pnl == 5.0  # shares = 5/0.5 = 10, payout = 10, pnl = 10 - 5
    assert risk.realized_pnl_usdc == 5.0


def test_settle_loss_computes_negative_pnl():
    risk = RiskManager(config=Config(dry_run=True))
    risk.record_open(make_position(size_usdc=5, entry_price=0.5))
    pnl = risk.settle("c1", won=False)
    assert pnl == -5.0
    assert risk.realized_pnl_usdc == -5.0


def test_settle_is_idempotent():
    risk = RiskManager(config=Config(dry_run=True))
    risk.record_open(make_position())
    risk.settle("c1", won=True)
    assert risk.settle("c1", won=True) is None
    assert risk.realized_pnl_usdc == 5.0


def test_daily_loss_limit_blocks_new_trades():
    config = Config(dry_run=True, max_daily_loss_usdc=10)
    risk = RiskManager(config=config)
    risk.record_open(make_position(condition_id="c1", size_usdc=10, entry_price=0.5))
    risk.settle("c1", won=False)  # pnl = -10
    assert risk.can_open_new_trade("c2") is False


def test_reset_daily_clears_pnl_and_settled_positions():
    risk = RiskManager(config=Config(dry_run=True))
    risk.record_open(make_position(condition_id="c1"))
    risk.settle("c1", won=True)
    risk.reset_daily()
    assert risk.realized_pnl_usdc == 0.0
    assert "c1" not in risk.positions

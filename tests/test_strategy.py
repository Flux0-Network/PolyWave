from polywave.strategy import MomentumStrategy, Signal


def test_momentum_up_when_above_threshold():
    strategy = MomentumStrategy(threshold_bps=15)
    assert strategy.decide(20) is Signal.UP


def test_momentum_down_when_below_negative_threshold():
    strategy = MomentumStrategy(threshold_bps=15)
    assert strategy.decide(-20) is Signal.DOWN


def test_momentum_skip_within_threshold_band():
    strategy = MomentumStrategy(threshold_bps=15)
    assert strategy.decide(5) is Signal.SKIP
    assert strategy.decide(-5) is Signal.SKIP
    assert strategy.decide(0) is Signal.SKIP


def test_momentum_boundary_is_inclusive():
    strategy = MomentumStrategy(threshold_bps=15)
    assert strategy.decide(15) is Signal.UP
    assert strategy.decide(-15) is Signal.DOWN

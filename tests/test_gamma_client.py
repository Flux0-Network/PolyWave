import json
from unittest.mock import MagicMock

from polywave.config import Config
from polywave.gamma_client import GammaClient, WINDOW_SECONDS


def make_raw_market(window_start, closed=False, outcome_prices=None):
    return {
        "conditionId": "0xabc",
        "slug": f"btc-updown-5m-{window_start}",
        "question": "Bitcoin Up or Down",
        "outcomes": json.dumps(["Up", "Down"]),
        "clobTokenIds": json.dumps(["111", "222"]),
        "outcomePrices": json.dumps(outcome_prices or ["0.5", "0.5"]),
        "acceptingOrders": True,
        "closed": closed,
    }


def session_returning(markets_by_slug):
    session = MagicMock()

    def get(url, params=None, timeout=None):
        slug = params["slug"]
        resp = MagicMock()
        resp.json.return_value = [markets_by_slug[slug]] if slug in markets_by_slug else []
        resp.raise_for_status.return_value = None
        return resp

    session.get.side_effect = get
    return session


def test_get_market_for_window_parses_fields():
    window_start = 1_700_000_000
    raw = make_raw_market(window_start)
    session = session_returning({f"btc-updown-5m-{window_start}": raw})
    client = GammaClient(Config(dry_run=True), session=session)

    market = client.get_market_for_window(window_start)

    assert market is not None
    assert market.condition_id == "0xabc"
    assert market.window_start == window_start
    assert market.window_end == window_start + WINDOW_SECONDS
    assert market.token_id_for("Up") == "111"
    assert market.token_id_for("Down") == "222"


def test_get_market_for_window_missing_returns_none():
    session = session_returning({})
    client = GammaClient(Config(dry_run=True), session=session)
    assert client.get_market_for_window(123) is None


def test_winning_outcome_none_until_closed():
    raw = make_raw_market(1_700_000_000, closed=False, outcome_prices=["0.4", "0.6"])
    session = session_returning({"btc-updown-5m-1700000000": raw})
    client = GammaClient(Config(dry_run=True), session=session)
    market = client.get_market_for_window(1_700_000_000)
    assert market.winning_outcome() is None


def test_winning_outcome_after_close():
    raw = make_raw_market(1_700_000_000, closed=True, outcome_prices=["1", "0"])
    session = session_returning({"btc-updown-5m-1700000000": raw})
    client = GammaClient(Config(dry_run=True), session=session)
    market = client.get_market_for_window(1_700_000_000)
    assert market.winning_outcome() == "Up"


def test_token_id_for_unknown_outcome_raises():
    raw = make_raw_market(1_700_000_000)
    session = session_returning({"btc-updown-5m-1700000000": raw})
    client = GammaClient(Config(dry_run=True), session=session)
    market = client.get_market_for_window(1_700_000_000)
    try:
        market.token_id_for("Sideways")
        assert False, "expected ValueError"
    except ValueError:
        pass

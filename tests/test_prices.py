"""Tests for the daily price history (PLAN.md Phase 6a). No network: requests are faked."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app import prices
from app.db import get_db

TODAY = date(2024, 1, 10)


def day_list(start, end):
    d, out = start, []
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def bitstamp_page(days):
    return {'data': {'pair': 'BTC/USD', 'ohlc': [
        {'timestamp': str(prices.to_timestamp(d)), 'open': '1', 'high': '1', 'low': '1',
         'close': f'{40000 + d.toordinal() % 1000}.50', 'volume': '1'} for d in days]}}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise prices.requests.HTTPError(str(self.status))

    def json(self):
        return self.payload


@pytest.fixture
def bitstamp(monkeypatch):
    """Fake Bitstamp: serves `limit` days from `start`, never past `latest`"""
    calls = []
    state = {'latest': TODAY, 'fail': False}

    def get(url, params, timeout):
        calls.append(dict(params))
        if state['fail'] or 'bitstamp' not in url:
            return FakeResponse({}, 503)
        start = prices.from_timestamp(int(params['start']))
        days = day_list(start, min(state['latest'], start + timedelta(days=int(params['limit']) - 1)))
        return FakeResponse(bitstamp_page(days))

    monkeypatch.setattr(prices.requests, 'get', get)
    return calls, state


# ---------- Fetching ----------

def test_fetch_closes_parses_bitstamp(bitstamp):
    closes = prices.fetch_closes(date(2024, 1, 1), date(2024, 1, 3))
    # The fake price is 40000 + (day ordinal % 1000) + 0.50; 2024-01-01 has ordinal 738886
    assert closes == [(date(2024, 1, 1), D('40886.50')), (date(2024, 1, 2), D('40887.50')),
                      (date(2024, 1, 3), D('40888.50'))]


def test_fetch_closes_pages_through_long_ranges(bitstamp):
    calls, _ = bitstamp
    closes = prices.fetch_closes(date(2018, 1, 1), date(2023, 12, 31))
    assert len(closes) == len(day_list(date(2018, 1, 1), date(2023, 12, 31)))  # 2191 days
    assert len(calls) == 3                       # 1000 days per request
    assert all(c['step'] == 86400 for c in calls)
    assert closes[-1][0] == date(2023, 12, 31)   # nothing past the end date


def test_fetch_closes_falls_back_to_kraken_for_recent_days(monkeypatch):
    kraken_rows = [[prices.to_timestamp(d), '1', '1', '1', '41000.1', '1', '1', 1]
                   for d in day_list(date(2024, 1, 5), date(2024, 1, 10))]

    def get(url, params, timeout):
        if 'bitstamp' in url:
            return FakeResponse({}, 503)
        return FakeResponse({'error': [], 'result': {'XXBTZUSD': kraken_rows, 'last': 0}})

    monkeypatch.setattr(prices.requests, 'get', get)
    closes = prices.fetch_closes(date(2024, 1, 7), date(2024, 1, 9))
    assert closes == [(date(2024, 1, d), D('41000.1')) for d in (7, 8, 9)]


def test_fetch_closes_raises_when_every_source_fails(monkeypatch):
    monkeypatch.setattr(prices.requests, 'get', lambda url, params, timeout: FakeResponse({}, 500))
    with pytest.raises(prices.PriceHistoryError):
        prices.fetch_closes(date(2024, 1, 1), date(2024, 1, 3))


# ---------- Syncing into the database ----------

def stored(app):
    with app.app_context():
        return prices.load_closes(get_db())


def test_first_sync_fills_history_up_to_yesterday(app, bitstamp):
    with app.app_context():
        assert prices.sync(get_db(), today=TODAY) is True
    closes = stored(app)
    assert closes[0][0] == prices.HISTORY_START
    assert closes[-1][0] == date(2024, 1, 9)  # today's candle isn't finished yet
    assert len(closes) == len(day_list(prices.HISTORY_START, date(2024, 1, 9)))


def test_later_syncs_only_fetch_missing_days(app, bitstamp):
    calls, state = bitstamp
    with app.app_context():
        prices.sync(get_db(), today=TODAY)
        calls.clear()
        assert prices.sync(get_db(), today=TODAY) is True      # up to date: no request
        assert calls == []
        state['latest'] = TODAY + timedelta(days=3)   # three more days have happened
        prices.sync(get_db(), today=TODAY + timedelta(days=3))
    assert prices.from_timestamp(int(calls[0]['start'])) == date(2024, 1, 10)
    assert stored(app)[-1][0] == date(2024, 1, 12)


def test_failed_sync_keeps_what_is_stored_and_waits_before_retrying(app, bitstamp, monkeypatch):
    calls, state = bitstamp
    clock = {'now': 1000.0}
    monkeypatch.setattr(prices.time, 'time', lambda: clock['now'])
    with app.app_context():
        prices.sync(get_db(), today=TODAY)
        before = len(prices.load_closes(get_db()))
        state['fail'] = True
        state['latest'] = TODAY + timedelta(days=2)
        calls.clear()
        assert prices.sync(get_db(), today=TODAY + timedelta(days=2)) is False
        tried = len(calls)
        assert tried > 0
        assert prices.sync(get_db(), today=TODAY + timedelta(days=2)) is False  # too soon to retry
        assert len(calls) == tried
        clock['now'] += prices.SYNC_RETRY_SECONDS + 1
        state['fail'] = False
        assert prices.sync(get_db(), today=TODAY + timedelta(days=2)) is True
        assert len(prices.load_closes(get_db())) == before + 2


def test_sync_twice_never_duplicates_days(app, bitstamp):
    with app.app_context():
        db = get_db()
        prices.sync(db, today=TODAY)
        prices.store_closes(db, [(date(2024, 1, 9), D('1'))])  # already stored: ignored
        closes = prices.load_closes(db)
    assert len({d for d, _ in closes}) == len(closes)
    assert closes[-1][1] != D('1')


def test_kraken_is_not_used_when_it_cannot_reach_back_far_enough(monkeypatch):
    # Kraken only has recent days; filling an old range from it would leave a permanent hole
    recent = [[prices.to_timestamp(d), '1', '1', '1', '41000', '1', '1', 1]
              for d in day_list(date(2024, 1, 5), date(2024, 1, 10))]

    def get(url, params, timeout):
        if 'bitstamp' in url:
            return FakeResponse({}, 503)
        return FakeResponse({'error': [], 'result': {'XXBTZUSD': recent, 'last': 0}})

    monkeypatch.setattr(prices.requests, 'get', get)
    with pytest.raises(prices.PriceHistoryError):
        prices.fetch_closes(date(2023, 1, 1), date(2024, 1, 9))


def test_kraken_error_response_is_a_failure(monkeypatch):
    def get(url, params, timeout):
        if 'bitstamp' in url:
            return FakeResponse({}, 503)
        return FakeResponse({'error': ['EGeneral:Too many requests'], 'result': {}})

    monkeypatch.setattr(prices.requests, 'get', get)
    with pytest.raises(prices.PriceHistoryError):
        prices.fetch_closes(date(2024, 1, 1), date(2024, 1, 3))


def test_bitstamp_with_no_data_yet_returns_nothing(monkeypatch):
    monkeypatch.setattr(prices.requests, 'get',
                        lambda url, params, timeout: FakeResponse({'data': {'pair': 'BTC/USD', 'ohlc': []}}))
    assert prices.fetch_closes(date(2024, 1, 1), date(2024, 1, 3)) == []

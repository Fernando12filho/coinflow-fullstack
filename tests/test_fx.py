"""Tests for exchange rates (PLAN.md Phase 7.1). No network: requests are faked."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from app import fx
from app.db import get_db

# Rates are "units of currency per 1 USD"
RATES = {
    '2024-03-14': {'BRL': '4.9800', 'EUR': '0.91600', 'GBP': '0.78300'},
    '2024-03-15': {'BRL': '5.0001', 'EUR': '0.91811', 'GBP': '0.78415'},   # a Friday
    '2024-03-18': {'BRL': '5.0200', 'EUR': '0.92000', 'GBP': '0.78600'},   # the next Monday
}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise fx.requests.HTTPError(str(self.status))

    def json(self):
        return self.payload


@pytest.fixture
def frankfurter(monkeypatch):
    calls, state = [], {'fail': False}

    def get(url, params, timeout):
        calls.append((url, dict(params)))
        if state['fail']:
            return FakeResponse({}, 503)
        start, end = url.rsplit('/', 1)[1].split('..')
        rates = {day: values for day, values in RATES.items() if start <= day <= end}
        return FakeResponse({'amount': 1.0, 'base': 'USD', 'rates': rates})

    monkeypatch.setattr(fx.requests, 'get', get)
    return calls, state


# ---------- Fetching and syncing ----------

def test_fetch_rates(frankfurter):
    calls, _ = frankfurter
    rows = fx.fetch_rates(date(2024, 3, 14), date(2024, 3, 15))
    url, params = calls[0]
    assert url == 'https://api.frankfurter.dev/v1/2024-03-14..2024-03-15'
    assert params == {'from': 'USD', 'to': 'BRL,EUR,GBP'}
    assert (date(2024, 3, 15), 'BRL', D('5.0001')) in rows
    assert len(rows) == 6


def test_sync_stores_rates_once(app, frankfurter, monkeypatch):
    calls, _ = frankfurter
    clock = {'now': 10_000.0}
    monkeypatch.setattr(fx.time, 'time', lambda: clock['now'])
    with app.app_context():
        db = get_db()
        assert fx.sync(db, today=date(2024, 3, 18)) is True
        assert calls[0][0].endswith(f'/{fx.RATES_START.isoformat()}..2024-03-18')
        assert fx.sync(db, today=date(2024, 3, 18)) is True      # synced recently: no request
        assert len(calls) == 1
        clock['now'] += fx.SYNC_INTERVAL_SECONDS + 1
        fx.sync(db, today=date(2024, 3, 19))
        assert calls[1][0].endswith('/2024-03-19..2024-03-19')   # only days after the last stored one
        assert fx.last_stored_day(db) == date(2024, 3, 18)


def test_failed_sync_waits_before_retrying(app, frankfurter, monkeypatch):
    calls, state = frankfurter
    clock = {'now': 10_000.0}
    monkeypatch.setattr(fx.time, 'time', lambda: clock['now'])
    state['fail'] = True
    with app.app_context():
        assert fx.sync(get_db(), today=date(2024, 3, 18)) is False
        assert fx.sync(get_db(), today=date(2024, 3, 18)) is False
        assert len(calls) == 1
        clock['now'] += fx.RETRY_SECONDS + 1
        state['fail'] = False
        assert fx.sync(get_db(), today=date(2024, 3, 18)) is True


# ---------- Converting ----------

@pytest.fixture
def converter(app, frankfurter):
    with app.app_context():
        fx.sync(get_db(), today=date(2024, 3, 18))
        return fx.load_converter(get_db())


def test_same_currency_needs_no_rate(converter):
    assert converter.convert(D('123.45'), 'BRL', 'BRL', date(1990, 1, 1)) == D('123.45')
    assert converter.rate('USD', date(1990, 1, 1)) == 1


def test_usd_to_brl_on_the_trade_date(converter):
    assert converter.convert(D('100'), 'USD', 'BRL', date(2024, 3, 15)) == D('500.01')


def test_weekends_use_the_previous_business_day(converter):
    saturday = date(2024, 3, 16)
    assert converter.rate('BRL', saturday) == D('5.0001')
    assert converter.convert(D('100'), 'USD', 'EUR', saturday) == D('91.811')


def test_brl_to_eur_goes_through_usd(converter):
    # R$500.01 on 2024-03-15 = $100 = €91.811
    assert converter.convert(D('500.01'), 'BRL', 'EUR', date(2024, 3, 15)) == D('91.811')


def test_missing_rates_are_refused_not_guessed(converter):
    with pytest.raises(fx.RateUnavailable, match='BRL'):
        converter.rate('BRL', date(2024, 3, 13))                       # before the first rate
    with pytest.raises(fx.RateUnavailable):
        converter.rate('BRL', date(2024, 3, 18) + timedelta(days=fx.LOOKBACK_DAYS + 1))  # too stale
    with pytest.raises(fx.RateUnavailable):
        converter.rate('JPY', date(2024, 3, 15))                       # not supported


def test_latest_rate_is_used_for_today(converter):
    assert converter.rate('GBP', date(2024, 3, 20)) == D('0.78600')

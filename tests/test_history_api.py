"""Tests for GET /api/bitcoin/history (PLAN.md Phase 6b). Price sources are faked."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from app import prices


def utc_today():
    return datetime.now(timezone.utc).date()


def fake_history(monkeypatch, last_close='40000', days=30):
    """Fake source: the last `days` finished days, rising by $10 a day, ending at `last_close`"""
    calls = []

    def fetch(start, end):
        calls.append((start, end))
        first = max(start, end - timedelta(days=days - 1))
        out, day = [], first
        while day <= end:
            out.append((day, D(last_close) - 10 * (end - day).days))
            day += timedelta(days=1)
        return out

    monkeypatch.setattr(prices, 'fetch_closes', fetch)
    return calls


def test_history_requires_login(client):
    assert client.get('/api/bitcoin/history').status_code == 401


def test_history_returns_daily_closes(logged_in, monkeypatch):
    fake_history(monkeypatch)
    body = logged_in.get('/api/bitcoin/history').get_json()
    assert body['success'] is True
    assert body['currency'] == 'USD'
    assert body['up_to_date'] is True
    closes = body['closes']
    assert len(closes) == 30
    assert closes[-1] == {'date': (utc_today() - timedelta(days=1)).isoformat(), 'close': '40000'}
    assert closes[0]['close'] == '39710'
    assert [c['date'] for c in closes] == sorted(c['date'] for c in closes)


def test_history_is_only_fetched_once_a_day(logged_in, monkeypatch):
    calls = fake_history(monkeypatch)
    logged_in.get('/api/bitcoin/history')
    logged_in.get('/api/bitcoin/history')
    assert len(calls) == 1


def test_change_since_yesterdays_close(logged_in, monkeypatch):
    # Live price is $50,000 in tests; yesterday closed at $40,000 -> +25%
    fake_history(monkeypatch, last_close='40000')
    change = logged_in.get('/api/bitcoin/history').get_json()['day_change']
    assert change == {'since': (utc_today() - timedelta(days=1)).isoformat(), 'close': '40000', 'percent': '25'}


def test_no_change_without_a_live_price(logged_in, monkeypatch):
    from app import bitcoin
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: None)
    fake_history(monkeypatch)
    assert logged_in.get('/api/bitcoin/history').get_json()['day_change'] is None


def test_history_when_sources_are_down(logged_in, monkeypatch):
    def fail(start, end):
        raise prices.PriceHistoryError('down')

    monkeypatch.setattr(prices, 'fetch_closes', fail)
    body = logged_in.get('/api/bitcoin/history').get_json()
    assert body['success'] is True
    assert (body['up_to_date'], body['closes'], body['day_change']) == (False, [], None)

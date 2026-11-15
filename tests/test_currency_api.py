"""Tests for showing amounts in the user's currency (PLAN.md Phase 7.3).

Fake exchange rates: 1 USD = R$5 = €0.90 = £0.80 on every day. The live BTC price is $50,000.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D

import pytest

from app import fx, prices


@pytest.fixture
def rates(monkeypatch):
    calls = []

    def fetch(start, end):
        calls.append((start, end))
        out, day = [], start
        while day <= end:
            out += [(day, 'BRL', D('5')), (day, 'EUR', D('0.90')), (day, 'GBP', D('0.80'))]
            day += timedelta(days=1)
        return out

    monkeypatch.setattr(fx, 'RATES_START', date(2023, 12, 1))
    monkeypatch.setattr(fx, 'fetch_rates', fetch)
    return calls


@pytest.fixture
def rates_down(monkeypatch):
    def fail(start, end):
        raise ConnectionError('offline')
    monkeypatch.setattr(fx, 'fetch_rates', fail)


def use(client, currency):
    assert client.put('/api/settings', json={'currency': currency}).status_code == 200


def add(client, **fields):
    body = {'side': 'buy', 'date': '2024-01-10', 'btc': '1', 'fiat': '30000'}
    body.update(fields)
    response = client.post('/api/trades', json=body)
    assert response.status_code == 201, response.get_json()
    return response.get_json()['trade']['id']


def test_usd_trades_shown_in_reais(logged_in, rates):
    add(logged_in)                     # 1 BTC for $30,000
    use(logged_in, 'BRL')
    p = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert p['currency'] == 'BRL'
    assert (p['invested'], p['break_even'], p['price'], p['value']) == ('150000', '150000', '250000', '250000')
    assert p['total_pnl'] == '100000'

    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['currency'], t['fiat'], t['price']) == ('BRL', '150000', '150000')
    # The original amounts are kept alongside, for editing
    assert (t['trade_currency'], t['trade_fiat'], t['trade_fee']) == ('USD', '30000', '0')


def test_new_trades_are_entered_in_the_display_currency(logged_in, rates):
    use(logged_in, 'BRL')
    add(logged_in, fiat='150000')      # R$150,000
    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['trade_currency'], t['trade_fiat']) == ('BRL', '150000')
    use(logged_in, 'USD')
    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['currency'], t['fiat']) == ('USD', '30000')


def test_trades_in_different_currencies_combine(logged_in, rates):
    add(logged_in)                                         # USD: 1 BTC for $30,000
    use(logged_in, 'BRL')
    add(logged_in, side='sell', date='2024-02-01', btc='0.5', fiat='100000', fee='50')  # R$100,000 + R$50 fee
    use(logged_in, 'USD')
    p = logged_in.get('/api/portfolio').get_json()['portfolio']
    # Sale: R$100,000 = $20,000, fee R$50 = $10 -> proceeds $19,990; cost removed 0.5 x $30,000
    assert (p['proceeds'], p['fees'], p['realized_pnl']) == ('19990', '10', '4990')


def test_btc_fees_are_not_converted(logged_in, rates):
    add(logged_in, fee='0.001', fee_asset='BTC')
    use(logged_in, 'EUR')
    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['fee'], t['fee_asset'], t['fiat']) == ('0.001', 'BTC', '27000')


def test_editing_keeps_the_trades_own_currency(logged_in, rates):
    trade_id = add(logged_in)          # USD
    use(logged_in, 'BRL')
    logged_in.put(f'/api/trades/{trade_id}', json={'side': 'buy', 'date': '2024-01-10', 'btc': '1', 'fiat': '31000'})
    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['trade_currency'], t['trade_fiat']) == ('USD', '31000')
    logged_in.put(f'/api/trades/{trade_id}', json={'side': 'buy', 'date': '2024-01-10', 'btc': '1',
                                                   'fiat': '28000', 'currency': 'EUR'})
    t = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (t['trade_currency'], t['trade_fiat']) == ('EUR', '28000')


def test_unsupported_trade_currency_is_rejected(logged_in, rates):
    response = logged_in.post('/api/trades', json={'side': 'buy', 'btc': '1', 'fiat': '1', 'currency': 'JPY'})
    assert response.status_code == 400
    assert 'Currency' in response.get_json()['error']


def test_usd_needs_no_exchange_rates(logged_in, rates_down):
    add(logged_in)
    assert logged_in.get('/api/portfolio').status_code == 200
    assert logged_in.get('/api/trades').status_code == 200


def test_missing_rates_are_explained_not_guessed(logged_in, rates_down):
    add(logged_in)
    use(logged_in, 'BRL')
    for url in ('/api/portfolio', '/api/trades'):
        response = logged_in.get(url)
        assert response.status_code == 503, url
        assert "Exchange rates aren't available" in response.get_json()['error']


def test_saving_works_without_exchange_rates(logged_in, rates_down):
    use(logged_in, 'BRL')
    add(logged_in, fiat='150000')
    add(logged_in, side='sell', date='2024-02-01', btc='0.5', fiat='100000')
    response = logged_in.post('/api/trades', json={'side': 'sell', 'date': '2024-03-01', 'btc': '1', 'fiat': '1'})
    assert response.status_code == 400            # the BTC balance check still runs
    assert 'only 0.5 BTC is held' in response.get_json()['error']


def test_price_history_in_reais(logged_in, rates, monkeypatch):
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    monkeypatch.setattr(prices, 'fetch_closes', lambda start, end: [(yesterday - timedelta(days=1), D('39000')),
                                                                    (yesterday, D('40000'))])
    use(logged_in, 'BRL')
    body = logged_in.get('/api/bitcoin/history').get_json()
    assert body['currency'] == 'BRL'
    assert [c['close'] for c in body['closes']] == ['195000', '200000']
    assert body['day_change']['percent'] == '25'      # R$250,000 now vs R$200,000


def test_price_history_without_exchange_rates(logged_in, rates_down, monkeypatch):
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    monkeypatch.setattr(prices, 'fetch_closes', lambda start, end: [(yesterday, D('40000'))])
    use(logged_in, 'BRL')
    response = logged_in.get('/api/bitcoin/history')
    assert response.status_code == 503
    assert "Exchange rates aren't available" in response.get_json()['error']


def test_trade_is_saved_even_if_it_cannot_be_shown_converted(logged_in, rates_down):
    add(logged_in)                     # a USD trade
    use(logged_in, 'BRL')              # shown in BRL, but no rates
    response = logged_in.post('/api/trades', json={'side': 'buy', 'date': '2024-02-01', 'btc': '1', 'fiat': '1',
                                                   'currency': 'USD'})
    assert response.status_code == 201
    assert set(response.get_json()['trade']) == {'id'}
    use(logged_in, 'USD')
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 2

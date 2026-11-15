"""Tests for the trade ledger storage and API (PLAN.md Phase 3)."""
from datetime import date

import pytest

from app import bitcoin
from app.db import create_tables, get_db, table_exists
from conftest import register, login


def add(client, **fields):
    body = {'side': 'buy', 'date': '2024-01-10', 'btc': '0.5', 'fiat': '20000'}
    body.update(fields)
    return client.post('/api/trades', json=body)


# ---------- Create + list ----------

def test_trades_require_login(client):
    assert client.get('/api/trades').status_code == 401
    assert client.post('/api/trades', json={}).status_code == 401
    assert client.get('/api/portfolio').status_code == 401


def test_add_and_list_a_buy(logged_in):
    response = add(logged_in, fee='10', notes='  first stack  ')
    assert response.status_code == 201
    trade_id = response.get_json()['trade']['id']

    trades = logged_in.get('/api/trades').get_json()['trades']
    assert trades == [{
        'id': trade_id,
        'side': 'buy',
        'date': '2024-01-10',
        'btc': '0.5',
        'fiat': '20000',
        'price': '40000',
        'fee': '10',
        'fee_asset': 'USD',
        'currency': 'USD',
        'notes': 'first stack',
        'source': 'manual',
        'held': '0.5',
        'break_even': '40020',
        'average_cost': '40020',
        'realized_pnl': None,
        'trade_currency': 'USD',
        'trade_fiat': '20000',
        'trade_fee': '10',
    }]


def test_amounts_keep_full_precision(logged_in):
    add(logged_in, btc='0.1', fiat='10')
    add(logged_in, btc='0.2', fiat='20', date='2024-01-11')
    portfolio = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert portfolio['held'] == '0.3'


def test_numbers_are_accepted_as_well_as_strings(logged_in):
    assert add(logged_in, btc=0.25, fiat=10000).status_code == 201
    assert logged_in.get('/api/trades').get_json()['trades'][0]['btc'] == '0.25'


def test_trades_are_listed_newest_first_with_running_values(logged_in):
    add(logged_in, date='2024-01-01', btc='1', fiat='100')
    add(logged_in, date='2024-01-03', side='sell', btc='0.5', fiat='100')
    add(logged_in, date='2024-01-02', btc='1', fiat='300')
    trades = logged_in.get('/api/trades').get_json()['trades']
    assert [t['date'] for t in trades] == ['2024-01-03', '2024-01-02', '2024-01-01']
    # Running break-even after each trade: 100, then 400/2 = 200, then (400-100)/1.5 = 200
    assert [t['break_even'] for t in trades] == ['200', '200', '100']
    # Sale of 0.5 BTC at $200 average cost for $100 -> realized $0
    assert trades[0]['realized_pnl'] == '0'


def test_reward_and_btc_fee(logged_in):
    add(logged_in, btc='1', fiat='100', fee='0.01', fee_asset='BTC')
    assert add(logged_in, side='reward', btc='0.01', fiat='0', date='2024-01-11').status_code == 201
    portfolio = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert portfolio['held'] == '1'
    assert portfolio['rewards'] == 1


def test_default_date_is_today(logged_in):
    body = {'side': 'buy', 'btc': '0.1', 'fiat': '100'}
    assert logged_in.post('/api/trades', json=body).status_code == 201
    trade = logged_in.get('/api/trades').get_json()['trades'][0]
    assert trade['date'] == date.today().isoformat()


# ---------- Validation ----------

@pytest.mark.parametrize('fields, message', [
    ({'side': 'gift'}, 'side'),
    ({'btc': '0'}, 'BTC amount'),
    ({'btc': '-1'}, 'BTC amount'),
    ({'btc': 'abc'}, 'BTC amount'),
    ({'btc': True}, 'BTC amount'),
    ({'btc': 'NaN'}, 'BTC amount'),
    ({'btc': 'Infinity'}, 'BTC amount'),
    ({'btc': '0.123456789'}, '8 decimal places'),
    ({'btc': '21000001'}, 'BTC amount'),
    ({'btc': None}, 'BTC amount'),
    ({'fiat': '0'}, 'fiat amount'),
    ({'fiat': '1e15'}, 'fiat amount'),
    ({'fee': '-1'}, 'Fee'),
    ({'fee_asset': 'EUR'}, 'Fee'),
    ({'side': 'reward', 'fiat': '5'}, 'fiat amount'),
    ({'date': '2999-01-01'}, 'future'),
    ({'date': 'yesterday'}, 'date'),
    ({'notes': 123}, 'Notes'),
    ({'notes': 'x' * 501}, 'Notes'),
])
def test_invalid_trades_are_rejected(logged_in, fields, message):
    response = add(logged_in, **fields)
    assert response.status_code == 400
    assert message in response.get_json()['error']


def test_non_json_body_is_rejected(logged_in):
    assert logged_in.post('/api/trades', data='not json').status_code == 400


def test_cannot_sell_more_than_held(logged_in):
    add(logged_in, btc='0.5', fiat='100')
    response = add(logged_in, side='sell', btc='0.6', fiat='200', date='2024-01-11')
    assert response.status_code == 400
    assert 'only 0.5 BTC is held' in response.get_json()['error']
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 1  # nothing was saved


def test_cannot_sell_before_buying(logged_in):
    add(logged_in, btc='1', fiat='100', date='2024-02-01')
    response = add(logged_in, side='sell', btc='0.5', fiat='60', date='2024-01-01')
    assert response.status_code == 400


# ---------- Edit + delete ----------

def test_edit_a_trade(logged_in):
    trade_id = add(logged_in).get_json()['trade']['id']
    response = logged_in.put(f'/api/trades/{trade_id}', json={
        'side': 'buy', 'date': '2024-01-12', 'btc': '0.4', 'fiat': '16000', 'notes': 'fixed typo',
    })
    assert response.status_code == 200
    trade = logged_in.get('/api/trades').get_json()['trades'][0]
    assert (trade['id'], trade['btc'], trade['date'], trade['notes']) == (trade_id, '0.4', '2024-01-12', 'fixed typo')


def test_edit_that_breaks_the_history_is_refused(logged_in):
    buy_id = add(logged_in, btc='1', fiat='100').get_json()['trade']['id']
    add(logged_in, side='sell', btc='0.8', fiat='100', date='2024-01-11')
    response = logged_in.put(f'/api/trades/{buy_id}', json={
        'side': 'buy', 'date': '2024-01-10', 'btc': '0.5', 'fiat': '50',
    })
    assert response.status_code == 400
    assert logged_in.get('/api/trades').get_json()['trades'][1]['btc'] == '1'  # unchanged


def test_delete_a_trade(logged_in):
    trade_id = add(logged_in).get_json()['trade']['id']
    assert logged_in.delete(f'/api/trades/{trade_id}').get_json()['success'] is True
    assert logged_in.get('/api/trades').get_json()['trades'] == []


def test_delete_that_breaks_the_history_is_refused(logged_in):
    buy_id = add(logged_in, btc='1', fiat='100').get_json()['trade']['id']
    add(logged_in, side='sell', btc='0.5', fiat='100', date='2024-01-11')
    response = logged_in.delete(f'/api/trades/{buy_id}')
    assert response.status_code == 400
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 2


def test_users_cannot_touch_each_others_trades(client):
    register(client)
    login(client)
    trade_id = add(client).get_json()['trade']['id']
    client.get('/auth/logout')

    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    assert client.get('/api/trades').get_json()['trades'] == []
    assert client.put(f'/api/trades/{trade_id}', json={'side': 'buy', 'btc': '1', 'fiat': '1'}).status_code == 404
    assert client.delete(f'/api/trades/{trade_id}').status_code == 404


# ---------- Portfolio summary ----------

def test_portfolio_summary(logged_in):
    # Buy 1 BTC for $100 (+$1 fee), sell 0.5 for $100. Price is $50,000 in tests.
    add(logged_in, btc='1', fiat='100', fee='1', date='2024-01-01')
    add(logged_in, side='sell', btc='0.5', fiat='100', date='2024-01-02')
    p = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert p['currency'] == 'USD'
    assert p['price'] == '50000'
    assert p['held'] == '0.5'
    assert p['invested'] == '101'
    assert p['proceeds'] == '100'
    assert p['fees'] == '1'
    assert p['break_even'] == '2'              # (101 - 100) / 0.5
    assert p['average_cost'] == '101'
    assert p['realized_pnl'] == '49.5'         # 100 - 0.5 * 101
    assert p['value'] == '25000'
    assert p['total_pnl'] == '24999'           # 100 + 25000 - 101
    assert p['unrealized_pnl'] == '24949.5'    # 25000 - 50.5
    assert (p['buys'], p['sells'], p['rewards']) == (1, 1, 0)


def test_portfolio_without_price(logged_in, monkeypatch):
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: None)
    add(logged_in)
    p = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert p['price'] is None
    assert p['value'] is None
    assert p['total_pnl'] is None
    assert p['held'] == '0.5'


def test_empty_portfolio(logged_in):
    p = logged_in.get('/api/portfolio').get_json()['portfolio']
    assert p['held'] == '0'
    assert p['break_even'] is None
    assert p['total_pnl'] == '0'


# ---------- Migration of old holdings ----------

LEGACY_HOLDING_TABLE = (
    'CREATE TABLE bitcoin_holding (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, '
    'amount REAL NOT NULL, purchase_price REAL NOT NULL, purchase_date TIMESTAMP NOT NULL, notes TEXT)'
)


def test_legacy_tables_are_not_created(app):
    with app.app_context():
        db = get_db()
        assert table_exists(db, 'trades')
        assert not table_exists(db, 'bitcoin_holding')
        assert not table_exists(db, 'transaction_history')


def test_old_holdings_move_into_trades_and_old_tables_are_dropped(app, logged_in):
    # A database from before Phase 3 still has the old tables
    with app.app_context():
        db = get_db()
        user_id = db.execute("SELECT id FROM users WHERE username = 'alice'").fetchone()['id']
        db.execute(LEGACY_HOLDING_TABLE)
        db.execute('CREATE TABLE transaction_history (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)')
        db.execute(
            'INSERT INTO bitcoin_holding (id, user_id, amount, purchase_price, purchase_date, notes) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (1, user_id, 0.005, 100000.0, '2024-03-15 00:00:00', 'old note'),
        )
        db.commit()
        create_tables()   # runs on every app start
        create_tables()   # running twice must not duplicate anything or fail
        assert not table_exists(db, 'bitcoin_holding')
        assert not table_exists(db, 'transaction_history')

    trades = logged_in.get('/api/trades').get_json()['trades']
    assert len(trades) == 1
    t = trades[0]
    assert (t['side'], t['date'], t['btc'], t['fiat'], t['notes'], t['source']) == (
        'buy', '2024-03-15', '0.005', '500', 'old note', 'manual')


# ---------- The old /api/bitcoin endpoints are gone (Phase 4 cleanup) ----------

@pytest.mark.parametrize('method, url', [
    ('get', '/api/bitcoin/holdings'),
    ('post', '/api/bitcoin/holdings'),
    ('delete', '/api/bitcoin/holdings/1'),
    ('get', '/api/bitcoin/transactions'),
])
def test_old_endpoints_are_removed(logged_in, method, url):
    assert getattr(logged_in, method)(url).status_code in (404, 405)


def test_price_endpoint_stays(client):
    assert client.get('/api/bitcoin/price').get_json()['success'] is True

"""Tests for importing exchange CSV files (PLAN.md Phase 5.3)."""
import io
from pathlib import Path

import pytest

from conftest import register, login

FIXTURES = Path(__file__).parent / 'fixtures'
KRAKEN = (FIXTURES / 'kraken' / 'ledgers.csv').read_bytes()
COINBASE = (FIXTURES / 'coinbase' / 'transactions.csv').read_bytes()
KRAKEN_LINES = KRAKEN.decode().splitlines()


def kraken_file(*line_numbers, extra=()):
    """A Kraken export made of the header plus the given fixture lines (1-based)"""
    rows = [KRAKEN_LINES[0]] + [KRAKEN_LINES[n - 1] for n in line_numbers] + list(extra)
    return ('\n'.join(rows) + '\n').encode()


def upload(client, url, content, name='ledgers.csv'):
    return client.post(url, data={'file': (io.BytesIO(content), name)}, content_type='multipart/form-data')


def preview(client, content, name='ledgers.csv'):
    return upload(client, '/api/imports/preview', content, name)


def confirm(client, content, name='ledgers.csv'):
    return upload(client, '/api/imports', content, name)


# ---------- Access ----------

def test_imports_require_login(client):
    assert preview(client, KRAKEN).status_code == 401
    assert confirm(client, KRAKEN).status_code == 401
    assert client.get('/api/imports').status_code == 401
    assert client.delete('/api/imports/1').status_code == 401


# ---------- Preview ----------

def test_preview_saves_nothing(logged_in):
    response = preview(logged_in, KRAKEN)
    assert response.status_code == 200
    p = response.get_json()['preview']
    assert p['provider'] == 'kraken'
    assert p['filename'] == 'ledgers.csv'
    assert (p['trades'], p['new'], p['duplicates']) == (5, 5, 0)
    assert (p['buys'], p['sells'], p['rewards']) == (3, 1, 1)
    assert (p['date_from'], p['date_to']) == ('2024-01-05', '2024-05-20')
    assert p['skipped_count'] == 6
    assert p['skipped'][0] == {'line': 2, 'reason': 'Deposit (moving money in or out of Kraken does not change '
                                                    'what you paid for BTC)'}
    assert p['already_imported'] is False
    assert p['problem'] is None
    assert logged_in.get('/api/trades').get_json()['trades'] == []


def test_preview_reports_an_impossible_history(logged_in):
    # Only the sale (lines 13-14): there's no BTC in CoinFlow to sell yet
    p = preview(logged_in, kraken_file(13, 14)).get_json()['preview']
    assert 'only 0 BTC is held' in p['problem']


@pytest.mark.parametrize('content, message', [
    (b'', "isn't a Kraken or Coinbase export"),
    (b'date,amount\n2024-01-01,5\n', "isn't a Kraken or Coinbase export"),
])
def test_unsupported_files_are_explained(logged_in, content, message):
    for response in (preview(logged_in, content), confirm(logged_in, content)):
        assert response.status_code == 400
        assert message in response.get_json()['error']


def test_a_file_is_required(logged_in):
    response = logged_in.post('/api/imports/preview', data={}, content_type='multipart/form-data')
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Choose a CSV file to import'


def test_files_over_5_mb_are_refused(logged_in):
    response = preview(logged_in, KRAKEN + b' ' * (5 * 1024 * 1024))
    assert response.status_code == 413
    assert 'too large' in response.get_json()['error']


# ---------- Import ----------

def test_import_kraken_file(logged_in):
    response = confirm(logged_in, KRAKEN)
    assert response.status_code == 201
    body = response.get_json()
    assert (body['added'], body['duplicates'], body['skipped']) == (5, 0, 6)

    trades = logged_in.get('/api/trades').get_json()['trades']
    assert len(trades) == 5
    assert {t['source'] for t in trades} == {'kraken'}
    assert trades[-1]['date'] == '2024-01-05'
    assert logged_in.get('/api/portfolio').get_json()['portfolio']['held'] == '0.015507'

    imports = logged_in.get('/api/imports').get_json()['imports']
    assert len(imports) == 1
    record = imports[0]
    assert (record['provider'], record['filename'], record['trade_count']) == ('kraken', 'ledgers.csv', 5)
    assert (record['date_from'], record['date_to']) == ('2024-01-05', '2024-05-20')


def test_import_coinbase_file(logged_in):
    response = confirm(logged_in, COINBASE, 'coinbase.csv')
    assert response.get_json()['added'] == 4
    assert logged_in.get('/api/portfolio').get_json()['portfolio']['held'] == '0.00801'


def test_the_same_file_cannot_be_imported_twice(logged_in):
    confirm(logged_in, KRAKEN)
    assert preview(logged_in, KRAKEN).get_json()['preview']['already_imported'] is True
    response = confirm(logged_in, KRAKEN, 'renamed.csv')
    assert response.status_code == 409
    assert 'already imported' in response.get_json()['error']
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 5


def test_overlapping_files_only_add_new_trades(logged_in):
    confirm(logged_in, kraken_file(3, 4, 13, 14))   # buy + sale
    # A later export repeats the sale and adds a new buy
    later = kraken_file(13, 14, extra=[
        '"LNEW01-CCCCC-000001","TNEW1-CCCCC-CCCCCC","2024-07-01 10:00:00","trade","tradespot","currency","fiat","USD","spot / main",-200.0000,0.5000,0',
        '"LNEW01-CCCCC-000002","TNEW1-CCCCC-CCCCCC","2024-07-01 10:00:00","trade","tradespot","currency","crypto","BTC","spot / main",0.0030000000,0.0000000000,0',
    ])
    p = preview(logged_in, later).get_json()['preview']
    assert (p['trades'], p['new'], p['duplicates']) == (2, 1, 1)
    body = confirm(logged_in, later).get_json()
    assert (body['added'], body['duplicates']) == (1, 1)
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 3


def test_a_file_with_nothing_new_is_refused(logged_in):
    confirm(logged_in, KRAKEN)
    same_trades = KRAKEN + b'\n'  # different bytes, same trades
    response = confirm(logged_in, same_trades)
    assert response.status_code == 400
    assert 'already in CoinFlow' in response.get_json()['error']


def test_an_impossible_history_is_refused(logged_in):
    response = confirm(logged_in, kraken_file(13, 14))
    assert response.status_code == 400
    assert 'only 0 BTC is held' in response.get_json()['error']
    assert logged_in.get('/api/trades').get_json()['trades'] == []
    assert logged_in.get('/api/imports').get_json()['imports'] == []


# ---------- Removing an import ----------

def test_remove_an_import_and_its_trades(logged_in):
    logged_in.post('/api/trades', json={'side': 'buy', 'date': '2023-01-01', 'btc': '1', 'fiat': '20000'})
    import_id = confirm(logged_in, KRAKEN).get_json()['import']['id']
    assert logged_in.delete(f'/api/imports/{import_id}').get_json()['success'] is True
    trades = logged_in.get('/api/trades').get_json()['trades']
    assert [t['source'] for t in trades] == ['manual']   # manual trades stay
    assert logged_in.get('/api/imports').get_json()['imports'] == []
    # Once removed, the same file can be imported again
    assert confirm(logged_in, KRAKEN).status_code == 201


def test_removing_an_import_a_later_sale_needs_is_refused(logged_in):
    import_id = confirm(logged_in, KRAKEN).get_json()['import']['id']
    logged_in.post('/api/trades', json={'side': 'sell', 'date': '2024-08-01', 'btc': '0.01', 'fiat': '600'})
    response = logged_in.delete(f'/api/imports/{import_id}')
    assert response.status_code == 400
    assert 'would break your history' in response.get_json()['error']
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 6


def test_users_cannot_see_or_remove_each_others_imports(client):
    register(client)
    login(client)
    import_id = confirm(client, KRAKEN).get_json()['import']['id']
    client.get('/auth/logout')

    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    assert client.get('/api/imports').get_json()['imports'] == []
    assert client.delete(f'/api/imports/{import_id}').status_code == 404
    # Bob can import the same file into his own account
    assert confirm(client, KRAKEN).status_code == 201

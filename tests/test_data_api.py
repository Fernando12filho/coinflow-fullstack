"""Tests for exporting and deleting your data (PLAN.md Phase 7.6 + 7.7)."""
import csv
import io
from datetime import date
from pathlib import Path

from conftest import register, login

KRAKEN = (Path(__file__).parent / 'fixtures' / 'kraken' / 'ledgers.csv').read_bytes()


def add(client, **fields):
    body = {'side': 'buy', 'date': '2024-01-10', 'btc': '0.5', 'fiat': '20000'}
    body.update(fields)
    assert client.post('/api/trades', json=body).status_code == 201


def exported(client):
    response = client.get('/api/trades/export')
    assert response.status_code == 200
    return response, list(csv.reader(io.StringIO(response.data.decode('utf-8'))))


# ---------- 7.6 Export ----------

def test_export_requires_login(client):
    assert client.get('/api/trades/export').status_code == 401


def test_export_is_a_csv_download(logged_in):
    response, rows = exported(logged_in)
    assert response.mimetype == 'text/csv'
    assert response.headers['Content-Disposition'] == \
        f'attachment; filename=coinflow-trades-{date.today().isoformat()}.csv'
    assert rows == [['date', 'type', 'btc', 'amount', 'currency', 'fee', 'fee_currency',
                     'price_per_btc', 'source', 'notes']]


def test_export_keeps_original_amounts_oldest_first(logged_in):
    add(logged_in, fee='10', notes='first stack')
    add(logged_in, side='sell', date='2024-02-01', btc='0.1', fiat='500', fee='0.0001', fee_asset='BTC',
        currency='BRL')
    logged_in.put('/api/settings', json={'currency': 'EUR'})   # display currency doesn't change the export
    _, rows = exported(logged_in)
    assert rows[1:] == [
        ['2024-01-10 00:00:00', 'buy', '0.5', '20000', 'USD', '10', 'USD', '40000', 'manual', 'first stack'],
        ['2024-02-01 00:00:00', 'sell', '0.1', '500', 'BRL', '0.0001', 'BTC', '5000', 'manual', ''],
    ]


def test_export_neutralises_spreadsheet_formulas(logged_in):
    add(logged_in, notes='=HYPERLINK("http://example.com")')
    _, rows = exported(logged_in)
    assert rows[1][-1] == '\'=HYPERLINK("http://example.com")'


def test_export_only_has_your_trades(client):
    register(client)
    login(client)
    add(client)
    client.get('/auth/logout')
    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    _, rows = exported(client)
    assert len(rows) == 1


# ---------- 7.7 Delete all data ----------

def test_delete_requires_login(client):
    assert client.post('/api/account/delete-data', json={'confirm': 'DELETE'}).status_code == 401


def test_delete_needs_the_word_delete(logged_in):
    add(logged_in)
    for body in ({}, {'confirm': 'delete'}, {'confirm': 'yes'}):
        response = logged_in.post('/api/account/delete-data', json=body)
        assert response.status_code == 400
        assert 'Type DELETE' in response.get_json()['error']
    assert len(logged_in.get('/api/trades').get_json()['trades']) == 1


def test_delete_removes_trades_imports_and_settings(logged_in):
    add(logged_in, date='2023-01-01')
    upload = logged_in.post('/api/imports', data={'file': (io.BytesIO(KRAKEN), 'ledgers.csv')},
                            content_type='multipart/form-data')
    assert upload.status_code == 201
    logged_in.put('/api/settings', json={'currency': 'BRL', 'btc_unit': 'sats'})

    response = logged_in.post('/api/account/delete-data', json={'confirm': 'DELETE'})
    assert response.get_json() == {'success': True, 'deleted': {'trades': 7, 'imports': 1}}
    assert logged_in.get('/api/trades').get_json()['trades'] == []
    assert logged_in.get('/api/imports').get_json()['imports'] == []
    assert logged_in.get('/api/settings').get_json()['settings']['currency'] == 'USD'
    # The account itself stays: still logged in, and the same file can be imported again
    upload = logged_in.post('/api/imports', data={'file': (io.BytesIO(KRAKEN), 'ledgers.csv')},
                            content_type='multipart/form-data')
    assert upload.status_code == 201


def test_delete_only_touches_your_data(client):
    register(client)
    login(client)
    add(client)
    client.get('/auth/logout')
    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    client.post('/api/account/delete-data', json={'confirm': 'DELETE'})
    client.get('/auth/logout')
    login(client)
    assert len(client.get('/api/trades').get_json()['trades']) == 1


def test_settings_page_has_data_section(logged_in):
    html = logged_in.get('/settings').data.decode()
    assert 'href="/api/trades/export"' in html
    assert 'id="delete-data-form"' in html

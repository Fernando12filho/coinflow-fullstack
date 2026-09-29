import os
import pytest
from app import create_app
from app import bitcoin
from app.db import init_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: 50000.0)
    bitcoin._price_cache.update(price=None, fetched_at=0.0)
    # Set TEST_DATABASE_URL to run the suite against Postgres instead of SQLite
    app = create_app({
        'TESTING': True,
        'DATABASE': str(tmp_path / 'test.sqlite'),
        'DATABASE_URL': os.environ.get('TEST_DATABASE_URL'),
    })
    with app.app_context():
        init_db()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, username='alice', email='alice@example.com', password='secret1'):
    return client.post('/auth/register', data={
        'username': username, 'email': email, 'password': password,
    })


def login(client, username='alice', password='secret1'):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_home_page_for_anonymous_user(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Track Your Bitcoin Journey' in response.data


def test_healthz(client):
    assert client.get('/healthz').get_json() == {'status': 'ok'}


def test_register_login_and_dashboard(client):
    assert register(client).headers['Location'] == '/auth/login'
    assert login(client).headers['Location'] == '/'
    assert b'Your Bitcoin Dashboard' in client.get('/dashboard').data


def test_duplicate_registration_is_rejected(client):
    register(client)
    response = register(client, email='ALICE@example.com')
    assert response.status_code == 200
    assert b'already registered' in response.data


def test_wrong_password(client):
    register(client)
    response = login(client, password='wrong-pass')
    assert b'Incorrect password' in response.data


def test_api_requires_login(client):
    response = client.get('/api/bitcoin/holdings')
    assert response.status_code == 401
    assert response.get_json()['success'] is False


def test_dashboard_redirects_anonymous_user(client):
    assert client.get('/dashboard').headers['Location'] == '/auth/login'


def test_price(client):
    assert client.get('/api/bitcoin/price').get_json() == {'success': True, 'price': 50000.0}


def test_holdings_profit_loss(client):
    register(client)
    login(client)
    response = client.post('/api/bitcoin/holdings', json={
        'amount': 0.5, 'purchase_price': 40000, 'notes': '<b>hi</b>',
    })
    assert response.get_json()['success'] is True

    data = client.get('/api/bitcoin/holdings').get_json()
    assert data['summary']['total_invested'] == 20000
    assert data['summary']['current_value'] == 25000
    assert data['summary']['total_profit_loss'] == 5000
    assert data['holdings'][0]['notes'] == '<b>hi</b>'

    holding_id = data['holdings'][0]['id']
    assert client.delete(f'/api/bitcoin/holdings/{holding_id}').get_json()['success'] is True
    assert client.get('/api/bitcoin/holdings').get_json()['holdings'] == []

    types = [t['type'] for t in client.get('/api/bitcoin/transactions').get_json()['transactions']]
    assert sorted(types) == ['BUY', 'SELL']


def test_invalid_holding(client):
    register(client)
    login(client)
    assert client.post('/api/bitcoin/holdings', json={'amount': -1, 'purchase_price': 5}).status_code == 400
    assert client.post('/api/bitcoin/holdings', json={'amount': 'abc', 'purchase_price': 5}).status_code == 400
    assert client.post('/api/bitcoin/holdings', data='not json').status_code == 400


def test_cannot_delete_other_users_holding(client):
    register(client)
    login(client)
    client.post('/api/bitcoin/holdings', json={'amount': 1, 'purchase_price': 1000})
    holding_id = client.get('/api/bitcoin/holdings').get_json()['holdings'][0]['id']
    client.get('/auth/logout')

    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    assert client.delete(f'/api/bitcoin/holdings/{holding_id}').status_code == 404


def test_newsletter_flow(client):
    assert client.post('/api/newsletter/subscribe', json={'email': 'x@example.com'}).status_code == 200
    assert client.post('/api/newsletter/subscribe', json={'email': 'x@example.com'}).status_code == 400
    assert client.post('/api/newsletter/subscribe', json={'email': 'bad'}).status_code == 400
    assert client.post('/api/newsletter/unsubscribe').status_code == 401

    register(client)
    login(client)
    client.post('/api/newsletter/subscribe', json={'email': 'alice@example.com'})
    status = client.get('/api/newsletter/status').get_json()
    assert status == {'success': True, 'subscribed': True, 'email': 'alice@example.com'}
    assert client.post('/api/newsletter/unsubscribe').get_json()['success'] is True
    assert client.get('/api/newsletter/status').get_json()['subscribed'] is False


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError):
        create_app({'TESTING': True})


def test_holdings_without_price_are_not_shown_as_a_loss(client, monkeypatch):
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: None)
    register(client)
    login(client)
    client.post('/api/bitcoin/holdings', json={'amount': 1, 'purchase_price': 1000})
    summary = client.get('/api/bitcoin/holdings').get_json()['summary']
    assert summary['total_invested'] == 1000
    assert summary['current_value'] is None
    assert summary['total_profit_loss'] is None
    assert client.get('/api/bitcoin/price').status_code == 500


def test_price_falls_back_to_next_source(app, monkeypatch):
    class Response:
        def __init__(self, url):
            self.url = url

        def raise_for_status(self):
            if 'coingecko' in self.url:
                raise bitcoin.requests.HTTPError('403 Forbidden')

        def json(self):
            return {'data': {'amount': '83521.92'}}

    monkeypatch.undo()
    monkeypatch.setattr(bitcoin.requests, 'get', lambda url, timeout: Response(url))
    with app.app_context():
        assert bitcoin._fetch_bitcoin_price() == 83521.92

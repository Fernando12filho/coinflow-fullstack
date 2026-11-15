import os
import pytest
from app import create_app
from app import bitcoin, fx, prices
from app.db import init_db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: 50000.0)
    bitcoin._price_cache.update(price=None, fetched_at=0.0)
    prices._state['last_failure'] = 0.0
    fx.reset_state()
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


def register(client, username='alice', email='alice@example.com', password='secret12'):
    return client.post('/auth/register', data={
        'username': username, 'email': email, 'password': password,
    })


def login(client, username='alice', password='secret12'):
    return client.post('/auth/login', data={'username': username, 'password': password})


@pytest.fixture
def logged_in(client):
    """A client with the default user registered and logged in"""
    register(client)
    login(client)
    return client

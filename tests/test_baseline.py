"""Baseline tests for existing behaviour that had no coverage (PLAN.md Phase 0)."""
import pytest
import requests
from app import bitcoin, newsletter
from conftest import register, login


@pytest.mark.parametrize('form, message', [
    ({'username': '', 'email': 'a@example.com', 'password': 'secret12'}, b'Username is required.'),
    ({'username': 'alice', 'email': '', 'password': 'secret12'}, b'Email is required.'),
    ({'username': 'alice', 'email': 'a@example.com', 'password': ''}, b'Password is required.'),
])
def test_register_requires_every_field(client, form, message):
    response = client.post('/auth/register', data=form)
    assert response.status_code == 200
    assert message in response.data






def test_logout_ends_the_session(logged_in):
    assert logged_in.get('/api/bitcoin/holdings').status_code == 200
    assert logged_in.get('/auth/logout').headers['Location'] == '/'
    assert logged_in.get('/api/bitcoin/holdings').status_code == 401


def test_dashboard_page_for_logged_in_user(logged_in):
    response = logged_in.get('/dashboard')
    assert response.status_code == 200
    assert b'Add Transaction' in response.data


def test_transactions_start_empty(logged_in):
    assert logged_in.get('/api/bitcoin/transactions').get_json() == {
        'success': True, 'transactions': [],
    }


def test_users_only_see_their_own_holdings(client):
    register(client)
    login(client)
    client.post('/api/bitcoin/holdings', json={'amount': 1, 'purchase_price': 1000})
    client.get('/auth/logout')

    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    assert client.get('/api/bitcoin/holdings').get_json()['holdings'] == []


def test_newsletter_subscribe_requires_email(client):
    response = client.post('/api/newsletter/subscribe', json={'email': '  '})
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Email is required'


def test_newsletter_accepts_form_data(client):
    response = client.post('/api/newsletter/subscribe', data={'email': 'form@example.com'})
    assert response.get_json()['success'] is True


def test_newsletter_resubscribe_reactivates(logged_in):
    logged_in.post('/api/newsletter/subscribe', json={'email': 'alice@example.com'})
    logged_in.post('/api/newsletter/unsubscribe')
    response = logged_in.post('/api/newsletter/subscribe', json={'email': 'alice@example.com'})
    assert response.get_json()['success'] is True
    assert logged_in.get('/api/newsletter/status').get_json()['subscribed'] is True


def test_unsubscribe_without_subscription(logged_in):
    response = logged_in.post('/api/newsletter/unsubscribe')
    assert response.status_code == 404
    assert response.get_json()['error'] == 'No active subscription found'


def test_newsletter_subscribe_handles_database_errors(client, monkeypatch):
    class BrokenDB:
        def execute(self, *args):
            raise RuntimeError('database is down')

        def rollback(self):
            pass

    monkeypatch.setattr(newsletter, 'get_db', lambda: BrokenDB())
    response = client.post('/api/newsletter/subscribe', json={'email': 'x@example.com'})
    assert response.status_code == 500
    assert response.get_json()['error'] == 'Subscription failed, please try again'


def test_price_is_none_when_every_source_fails(app, monkeypatch):
    def fail(url, timeout):
        raise requests.ConnectionError('offline')

    monkeypatch.undo()
    monkeypatch.setattr(bitcoin.requests, 'get', fail)
    with app.app_context():
        assert bitcoin._fetch_bitcoin_price() is None


def test_init_db_command_resets_data(app, logged_in):
    logged_in.post('/api/bitcoin/holdings', json={'amount': 1, 'purchase_price': 1000})
    # The real `flask` CLI pushes an app context before running commands
    with app.app_context():
        result = app.test_cli_runner().invoke(args=['init-db'])
    assert 'Initialized the database.' in result.output
    assert logged_in.get('/api/bitcoin/holdings').status_code == 401  # user is gone too

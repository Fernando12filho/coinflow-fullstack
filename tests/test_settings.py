"""Tests for user settings (PLAN.md Phase 7.2)."""
import re

import pytest

from conftest import register, login

DEFAULTS = {'currency': 'USD', 'btc_unit': 'BTC', 'locale': 'auto'}


def test_settings_require_login(client):
    assert client.get('/api/settings').status_code == 401
    assert client.put('/api/settings', json={}).status_code == 401
    assert client.get('/settings').headers['Location'] == '/auth/login'


def test_defaults(logged_in):
    body = logged_in.get('/api/settings').get_json()
    assert body['settings'] == DEFAULTS
    assert body['options']['currencies'] == ['USD', 'EUR', 'GBP', 'BRL']
    assert body['options']['btc_units'] == ['BTC', 'sats']
    assert {'code': 'pt-BR', 'label': 'Português (Brasil)'} in body['options']['locales']


def test_save_settings(logged_in):
    response = logged_in.put('/api/settings', json={'currency': 'BRL', 'btc_unit': 'sats', 'locale': 'pt-BR'})
    assert response.get_json() == {'success': True,
                                   'settings': {'currency': 'BRL', 'btc_unit': 'sats', 'locale': 'pt-BR'}}
    assert logged_in.get('/api/settings').get_json()['settings']['currency'] == 'BRL'


def test_partial_update_keeps_the_rest(logged_in):
    logged_in.put('/api/settings', json={'currency': 'EUR', 'btc_unit': 'sats'})
    logged_in.put('/api/settings', json={'locale': 'de-DE'})
    assert logged_in.get('/api/settings').get_json()['settings'] == {
        'currency': 'EUR', 'btc_unit': 'sats', 'locale': 'de-DE'}


@pytest.mark.parametrize('body, message', [
    ({'currency': 'JPY'}, 'Currency'),
    ({'currency': 5}, 'Currency'),
    ({'btc_unit': 'mBTC'}, 'Bitcoin unit'),
    ({'locale': 'xx-YY'}, 'Number format'),
    ({'theme': 'light'}, 'Unknown setting'),
])
def test_invalid_settings_are_rejected(logged_in, body, message):
    response = logged_in.put('/api/settings', json=body)
    assert response.status_code == 400
    assert message in response.get_json()['error']
    assert logged_in.get('/api/settings').get_json()['settings'] == DEFAULTS


def test_non_json_body_is_rejected(logged_in):
    assert logged_in.put('/api/settings', data='nope').status_code == 400


def test_settings_are_per_user(client):
    register(client)
    login(client)
    client.put('/api/settings', json={'currency': 'BRL'})
    client.get('/auth/logout')
    register(client, username='bob', email='bob@example.com')
    login(client, username='bob')
    assert client.get('/api/settings').get_json()['settings'] == DEFAULTS


def test_settings_page(logged_in):
    logged_in.put('/api/settings', json={'currency': 'GBP'})
    html = logged_in.get('/settings').data.decode()
    assert re.search(r'<a[^>]*class="pill active"[^>]*aria-current="page"[^>]*>Settings</a>', html)
    assert '<option value="GBP" selected>' in html
    for name in ('currency', 'btc_unit', 'locale'):
        assert f'name="{name}"' in html, name
    assert 'href="/settings"' in logged_in.get('/').data.decode()

import re

import pytest
from app import create_app
from app import bitcoin
from conftest import register, login


def test_home_page_sends_anonymous_user_to_login(client):
    assert client.get('/').headers['Location'] == '/auth/login'
    response = client.get('/auth/login')
    assert response.status_code == 200
    assert b'What is Coinflow?' in response.data


def test_register_page(client):
    response = client.get('/auth/register')
    assert response.status_code == 200
    assert b'Sign Up' in response.data


def test_healthz(client):
    assert client.get('/healthz').get_json() == {'status': 'ok'}


def test_register_login_and_dashboard(client):
    assert register(client).headers['Location'] == '/auth/login'
    assert login(client).headers['Location'] == '/'
    page = client.get('/').data
    assert b'Add Transaction' in page
    assert b'alice' in page
    assert b'Subscribe to our Newsletter' in client.get('/newsletter').data


def test_duplicate_registration_is_rejected(client):
    register(client)
    response = register(client, email='ALICE@example.com')
    assert response.status_code == 200
    assert b'already registered' in response.data


def test_wrong_password(client):
    register(client)
    response = login(client, password='wrong-pass')
    assert b'Invalid username or password.' in response.data


def test_api_requires_login(client):
    response = client.get('/api/trades')
    assert response.status_code == 401
    assert response.get_json()['success'] is False


def test_dashboard_redirects_anonymous_user(client):
    assert client.get('/dashboard').headers['Location'] == '/auth/login'


def test_price(client):
    assert client.get('/api/bitcoin/price').get_json() == {'success': True, 'price': 50000.0}


def test_trade_lifecycle(client):
    register(client)
    login(client)
    response = client.post('/api/trades', json={
        'side': 'buy', 'date': '2024-01-10', 'btc': '0.5', 'fiat': '20000', 'notes': '<b>hi</b>',
    })
    assert response.status_code == 201

    # Price is $50,000 in tests: 0.5 BTC is worth $25,000, a $5,000 gain
    portfolio = client.get('/api/portfolio').get_json()['portfolio']
    assert (portfolio['invested'], portfolio['value'], portfolio['total_pnl']) == ('20000', '25000', '5000')
    trade = client.get('/api/trades').get_json()['trades'][0]
    assert trade['notes'] == '<b>hi</b>'  # stored as plain text; the UI never renders it as HTML

    # Deleting is a correction, not a sale: the trade disappears entirely
    assert client.delete(f"/api/trades/{trade['id']}").get_json()['success'] is True
    assert client.get('/api/trades').get_json()['trades'] == []


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


def test_price_endpoint_reports_missing_price(client, monkeypatch):
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: None)
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


def test_newsletter_page_requires_login(client):
    assert client.get('/newsletter').headers['Location'] == '/auth/login'


# ---------- "Brushed MSX" restyle (STYLE_GUIDE.md §10) ----------


def pages(client):
    """HTML of every page: login and register logged out, dashboard and newsletter logged in"""
    out = {'login': client.get('/auth/login').data.decode(),
           'register': client.get('/auth/register').data.decode()}
    register(client)
    login(client)
    out['dashboard'] = client.get('/').data.decode()
    out['newsletter'] = client.get('/newsletter').data.decode()
    return out


def test_no_web_fonts_are_loaded(client):
    for name, html in pages(client).items():
        assert 'fonts.googleapis.com' not in html, name
        assert 'fonts.gstatic.com' not in html, name


def test_every_page_has_the_stripe_band(client):
    for name, html in pages(client).items():
        assert 'class="stripe-band' in html, name


def test_app_pages_sit_in_a_window(client):
    html = pages(client)
    for name in ('dashboard', 'newsletter'):
        assert 'class="window"' in html[name], name
        assert '<main class="app-main">' in html[name], name
    assert 'class="hero-row"' in html['dashboard']
    assert 'class="auth-box window"' in html['login']


def test_auth_inputs_have_visible_labels(client):
    html = pages(client)
    for name in ('login', 'register'):
        for field in ('username', 'password'):
            assert re.search(r'<label[^>]*>\s*\w+\s*<input[^>]*name="%s"' % field, html[name]), (name, field)
    assert re.search(r'<label[^>]*>\s*Email\s*<input[^>]*name="email"', html['register'])


def test_auth_pages_have_title_row_and_helper_line(client):
    html = pages(client)
    assert 'New here?' in html['login']
    assert 'Already have an account?' in html['register']
    assert 'At least 8 characters' in html['register']


def test_active_nav_link_is_marked(client):
    html = pages(client)
    assert re.search(r'<a[^>]*class="pill active"[^>]*aria-current="page"[^>]*>Portfolio</a>', html['dashboard'])
    assert re.search(r'<a[^>]*class="pill active"[^>]*aria-current="page"[^>]*>Newsletter</a>', html['newsletter'])
    assert html['dashboard'].count('aria-disabled="true"') == 2
    assert 'class="pill logout-button"' in html['dashboard']


def test_transactions_table_has_hidden_header_cells(client):
    html = pages(client)['dashboard']
    assert '<span class="visually-hidden">Stripe</span>' in html
    assert '<span class="visually-hidden">Actions</span>' in html


def test_tabs_and_dialog_are_accessible(client):
    html = pages(client)['dashboard']
    assert re.search(r'id="tab-assets-button"[^>]*aria-selected="true"[^>]*aria-controls="tab-assets"', html)
    assert re.search(r'id="tab-transactions-button"[^>]*aria-selected="false"[^>]*aria-controls="tab-transactions"', html)
    assert '✖' not in html
    assert re.search(r'class="pill pill-icon close-button"[^>]*aria-label="Close"', html)


def test_footer_has_no_emoji(client):
    for name, html in pages(client).items():
        assert '❤' not in html, name
        assert 'Made for Bitcoiners.' in html, name


def test_stylesheet_uses_the_design_tokens(client):
    css = client.get('/static/css/style.css').data.decode()
    for token in ('--desk:', '--metal:', '--paper:', '--amber:', '--s8:', '--font:'):
        assert token in css, token
    assert 'Barlow' not in css and 'Fira' not in css
    assert ':focus-visible' in css
    assert re.search(r'font-weight:\s*(500|600|800|900)', css) is None  # Lucida Grande has 400 + 700 only


def test_popups_are_themed_by_css_not_inline_colours(client):
    js = client.get('/static/js/main.js').data.decode()
    assert 'confirmButtonColor' not in js
    assert "confirmButton: 'swal-danger'" in js


def test_transactions_table_has_ledger_columns(client):
    html = pages(client)['dashboard']
    headers = re.findall(r'<th[^>]*>(.*?)</th>', html, re.S)
    visible = [re.sub(r'<[^>]+>', '', h).strip() for h in headers]
    assert visible == ['Stripe', 'Type', 'Date', 'BTC', 'Price / BTC', 'Fee',
                       'Break-even', 'Realized P&amp;L', 'Notes', 'Actions']


def test_trade_form_fields(client):
    html = pages(client)['dashboard']
    for side in ('buy', 'sell', 'reward'):
        assert f'name="side" value="{side}"' in html
    for name in ('date', 'btc', 'fiat', 'fee', 'notes'):
        assert f'name="{name}"' in html, name
    assert re.search(r'<select[^>]*name="fee_asset"', html)
    assert '<option value="BTC">BTC</option>' in html

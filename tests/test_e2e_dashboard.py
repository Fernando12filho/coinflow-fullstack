"""Browser tests for the dashboard (PLAN.md Phase 4).

Each test runs the real app on a local port with a fresh database and drives it
in headless Chromium. The BTC price is fixed at $50,000. Skipped when Playwright
or a Chromium build isn't available. Set PLAYWRIGHT_CHROMIUM to pick a browser.
"""
import glob
import os
import threading

import pytest
from werkzeug.serving import make_server

from app import bitcoin, create_app

sync_api = pytest.importorskip('playwright.sync_api')
expect = sync_api.expect

pytestmark = pytest.mark.e2e

PASSWORD = 'secret12'


def _chromium_path():
    if os.environ.get('PLAYWRIGHT_CHROMIUM'):
        return os.environ['PLAYWRIGHT_CHROMIUM']
    patterns = [
        '~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell',
        '~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell',
    ]
    found = sorted(path for p in patterns for path in glob.glob(os.path.expanduser(p)))
    return found[-1] if found else None  # None -> Playwright's own default browser


@pytest.fixture(scope='module')
def browser():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=_chromium_path())
        except Exception as e:  # no browser installed
            pytest.skip(f'Chromium not available: {e}')
        yield b
        b.close()


@pytest.fixture
def base_url(tmp_path, monkeypatch):
    """Run the app on a free local port with a fresh database"""
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setattr(bitcoin, '_fetch_bitcoin_price', lambda: 50000.0)
    bitcoin._price_cache.update(price=None, fetched_at=0.0)
    app = create_app({'TESTING': True, 'DATABASE': str(tmp_path / 'e2e.sqlite')})
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    pg = context.new_page()
    pg.set_default_timeout(5000)
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    yield pg
    context.close()
    assert errors == [], f'JavaScript errors: {errors}'


def sign_in(page, base_url):
    page.request.post(f'{base_url}/auth/register',
                      form={'username': 'alice', 'email': 'alice@example.com', 'password': PASSWORD})
    page.request.post(f'{base_url}/auth/login', form={'username': 'alice', 'password': PASSWORD})
    page.request.get(f'{base_url}/auth/register')  # use up flash messages so no popup covers the page


def add_trade(page, base_url, **fields):
    response = page.request.post(f'{base_url}/api/trades', data=fields)
    assert response.status == 201, response.text()
    return response.json()['trade']['id']


def open_dashboard(page, base_url):
    page.goto(f'{base_url}/')
    expect(page.locator('#btc-price span')).to_have_text('$50,000.00')


# ---------- 4a: position summary ----------

def test_dashboard_shows_position_stats(page, base_url):
    # Buy 1 BTC for $30,000, sell 0.5 for $25,000. Price $50,000.
    # Break-even (30000 - 25000) / 0.5 = $10,000. Average cost $30,000.
    # Realized 25000 - 15000 = $10,000. Unrealized 25000 - 15000 = $10,000 (+66.67%).
    # Total 25000 + 25000 - 30000 = $20,000 (+66.67%).
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000')
    add_trade(page, base_url, side='sell', date='2024-02-01', btc='0.5', fiat='25000')
    open_dashboard(page, base_url)

    expect(page.locator('#stat-break-even')).to_have_text('$10,000.00')
    expect(page.locator('#stat-average-cost')).to_have_text('$30,000.00')

    # P&L reveals the portfolio size, so it stays hidden until "Total" is shown
    expect(page.locator('#stat-realized')).to_have_text('********')
    expect(page.locator('#stat-unrealized')).to_have_text('********')
    page.click('[data-toggle="total-invested"]')
    expect(page.locator('#stat-realized')).to_have_text('+$10,000.00')
    expect(page.locator('#stat-realized')).to_have_class('stat-value profit')
    expect(page.locator('#stat-unrealized')).to_have_text('+$10,000.00 (+66.67%)')
    expect(page.locator('[data-value-id="total-invested"]')).to_have_text('$30,000.00')
    expect(page.locator('#total-profit-loss span')).to_have_text('+$20,000.00 (+66.67%)')

    page.click('[data-toggle="total-btc"]')
    expect(page.locator('[data-value-id="total-btc"]')).to_have_text('0.50000000')
    expect(page.locator('#asset-value')).to_have_text('Worth $25,000.00')


def test_break_even_below_zero_shows_free(page, base_url):
    # Buy 1 BTC for $100, sell 0.5 for $300 -> break-even -$400
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='100')
    add_trade(page, base_url, side='sell', date='2024-02-01', btc='0.5', fiat='300')
    open_dashboard(page, base_url)
    expect(page.locator('#stat-break-even')).to_have_text('Free')
    expect(page.locator('#stat-break-even-note')).to_contain_text('more than you invested')


def test_empty_portfolio(page, base_url):
    sign_in(page, base_url)
    open_dashboard(page, base_url)
    expect(page.locator('#stat-break-even')).to_have_text('—')
    expect(page.locator('#stat-average-cost')).to_have_text('—')
    expect(page.locator('#bitcoin-asset-card')).to_be_hidden()


# ---------- 4b: the real ledger in the Transactions tab ----------

def confirm_popup(page):
    page.click('.swal2-confirm')


def wait_for_popups_to_close(page):
    expect(page.locator('.swal2-container')).to_have_count(0)


def ledger_rows(page):
    """Visible text of each transactions row, without the chip and action cells"""
    return page.locator('#transactions-body tr').evaluate_all(
        "rows => rows.map(r => [...r.querySelectorAll('td:not(.cell-chip):not(.cell-actions)')]"
        ".map(td => td.textContent.trim()))")


def seed_ledger(page, base_url):
    # Buy 1 BTC for $30,000 + $10 fee; earn 0.01 BTC; sell 0.5 BTC for $25,000 paying 0.0001 BTC fee.
    # Break-even after each: 30010 / 1 = $30,010.00; 30010 / 1.01 = $29,712.87;
    # (30010 - 25000) / 0.5099 = $9,825.46.
    # Sale: 0.5001 BTC leave at $29,712.87 average -> realized 25000 - 14859.41 = +$10,140.59
    ids = {}
    ids['buy'] = add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000', fee='10',
                           notes='First stack')
    ids['reward'] = add_trade(page, base_url, side='reward', date='2024-01-15', btc='0.01')
    ids['sell'] = add_trade(page, base_url, side='sell', date='2024-02-01', btc='0.5', fiat='25000',
                            fee='0.0001', fee_asset='BTC')
    return ids


def test_transactions_tab_shows_the_ledger(page, base_url):
    sign_in(page, base_url)
    seed_ledger(page, base_url)
    open_dashboard(page, base_url)
    page.click('#tab-transactions-button')

    expect(page.locator('#transactions-body tr')).to_have_count(3)
    assert ledger_rows(page) == [
        ['Sell', 'Feb 1, 2024', '−0.50000000', '$50,000.00', '0.0001 BTC', '$9,825.46', '+$10,140.59', ''],
        ['Reward', 'Jan 15, 2024', '+0.01000000', '—', '—', '$29,712.87', '—', ''],
        ['Buy', 'Jan 1, 2024', '+1.00000000', '$30,000.00', '$10.00', '$30,010.00', '—', 'First stack'],
    ]
    expect(page.locator('#transactions-body tr').first.locator('td.cell-pnl')).to_have_class('num cell-pnl profit')
    expect(page.locator('#transactions-empty')).to_be_hidden()


def test_delete_a_trade_from_the_ledger(page, base_url):
    sign_in(page, base_url)
    ids = seed_ledger(page, base_url)
    open_dashboard(page, base_url)
    page.click('#tab-transactions-button')

    page.click(f'#transactions-body tr[data-id="{ids["reward"]}"] .delete-button')
    confirm_popup(page)
    expect(page.locator('#transactions-body tr')).to_have_count(2)
    wait_for_popups_to_close(page)


def test_deleting_a_buy_that_a_sale_needs_is_explained(page, base_url):
    sign_in(page, base_url)
    ids = seed_ledger(page, base_url)
    open_dashboard(page, base_url)
    page.click('#tab-transactions-button')

    page.click(f'#transactions-body tr[data-id="{ids["buy"]}"] .delete-button')
    confirm_popup(page)
    expect(page.locator('.swal2-html-container')).to_contain_text('would break your history')
    expect(page.locator('#transactions-body tr')).to_have_count(3)


def test_empty_ledger_message(page, base_url):
    sign_in(page, base_url)
    open_dashboard(page, base_url)
    page.click('#tab-transactions-button')
    expect(page.locator('#transactions-empty')).to_be_visible()
    expect(page.locator('#transactions-body tr')).to_have_count(0)


# ---------- 4c: add, edit, sell and reward through the form ----------

def open_form(page):
    page.click('.hero [data-open-popup]')
    expect(page.locator('#trade-popup')).to_be_visible()


def fill_form(page, side='buy', date=None, btc=None, fiat=None, fee=None, fee_asset=None, notes=None):
    page.check(f'#trade-form input[name="side"][value="{side}"]')
    if date is not None:
        page.fill('#trade-form input[name="date"]', date)
    if btc is not None:
        page.fill('#trade-form input[name="btc"]', btc)
    if fiat is not None:
        page.fill('#trade-form input[name="fiat"]', fiat)
    if fee is not None:
        page.fill('#trade-form input[name="fee"]', fee)
    if fee_asset is not None:
        page.select_option('#trade-form select[name="fee_asset"]', fee_asset)
    if notes is not None:
        page.fill('#trade-form textarea[name="notes"]', notes)


def save_form(page):
    page.click('#trade-form button[type="submit"]')


def show_ledger(page):
    page.click('#tab-transactions-button')


def test_add_a_buy_with_a_fee(page, base_url):
    sign_in(page, base_url)
    open_dashboard(page, base_url)
    open_form(page)
    expect(page.locator('#popup-title')).to_have_text('Add Transaction')
    fill_form(page, 'buy', date='2024-03-15', btc='0.25', fiat='15000', fee='7.50', notes='Form buy')
    expect(page.locator('#price-per-btc')).to_have_text('Price per BTC: $60,000.00')
    save_form(page)

    expect(page.locator('#trade-popup')).to_be_hidden()
    show_ledger(page)
    expect(page.locator('#transactions-body tr')).to_have_count(1)
    # Break-even: (15000 + 7.50) / 0.25 = $60,030.00
    assert ledger_rows(page) == [
        ['Buy', 'Mar 15, 2024', '+0.25000000', '$60,000.00', '$7.50', '$60,030.00', '—', 'Form buy'],
    ]


def test_add_a_sell_with_a_btc_fee(page, base_url):
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000')
    open_dashboard(page, base_url)
    open_form(page)
    fill_form(page, 'sell', date='2024-06-01', btc='0.4', fiat='20000', fee='0.0001', fee_asset='BTC')
    expect(page.locator('#fiat-label')).to_have_text('Amount received ($)')
    save_form(page)

    show_ledger(page)
    expect(page.locator('#transactions-body tr')).to_have_count(2)
    # 0.4001 BTC leave at $30,000 average cost -> realized 20000 - 12003 = +$7,997.00
    sell = ledger_rows(page)[0]
    assert sell[:3] == ['Sell', 'Jun 1, 2024', '−0.40000000']
    assert sell[4] == '0.0001 BTC'
    assert sell[6] == '+$7,997.00'


def test_reward_has_no_dollar_amount(page, base_url):
    sign_in(page, base_url)
    open_dashboard(page, base_url)
    open_form(page)
    fill_form(page, 'reward', date='2024-02-01', btc='0.01')
    expect(page.locator('#fiat-field')).to_be_hidden()
    expect(page.locator('#price-per-btc')).to_be_hidden()
    save_form(page)

    show_ledger(page)
    expect(page.locator('#transactions-body tr')).to_have_count(1)
    assert ledger_rows(page)[0][:4] == ['Reward', 'Feb 1, 2024', '+0.01000000', '—']


def test_edit_a_trade(page, base_url):
    sign_in(page, base_url)
    trade_id = add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000', notes='typo')
    open_dashboard(page, base_url)
    show_ledger(page)
    page.click(f'#transactions-body tr[data-id="{trade_id}"] .edit-button')

    expect(page.locator('#popup-title')).to_have_text('Edit Transaction')
    expect(page.locator('#trade-form input[name="side"][value="buy"]')).to_be_checked()
    expect(page.locator('#trade-form input[name="date"]')).to_have_value('2024-01-01')
    expect(page.locator('#trade-form input[name="btc"]')).to_have_value('1')
    expect(page.locator('#trade-form input[name="fiat"]')).to_have_value('30000')
    expect(page.locator('#trade-form textarea[name="notes"]')).to_have_value('typo')

    fill_form(page, 'buy', fiat='31000', notes='fixed')
    save_form(page)
    expect(page.locator('#trade-popup')).to_be_hidden()
    expect(page.locator('#transactions-body tr')).to_have_count(1)
    expect(page.locator(f'#transactions-body tr[data-id="{trade_id}"]')).to_contain_text('$31,000.00')
    expect(page.locator(f'#transactions-body tr[data-id="{trade_id}"] .notes-cell')).to_have_text('fixed')


def test_refused_sale_keeps_the_form_open(page, base_url):
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='0.5', fiat='15000')
    open_dashboard(page, base_url)
    open_form(page)
    fill_form(page, 'sell', date='2024-06-01', btc='1', fiat='60000')
    save_form(page)

    expect(page.locator('.swal2-html-container')).to_contain_text('only 0.5 BTC is held')
    confirm_popup(page)
    wait_for_popups_to_close(page)
    expect(page.locator('#trade-popup')).to_be_visible()  # nothing typed is lost
    expect(page.locator('#trade-form input[name="btc"]')).to_have_value('1')


def test_dialog_keyboard_focus(page, base_url):
    sign_in(page, base_url)
    trade_id = add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000')
    open_dashboard(page, base_url)

    # Open from the keyboard, focus moves into the form, Esc closes and focus returns
    page.focus('.hero [data-open-popup]')
    page.keyboard.press('Enter')
    expect(page.locator('#trade-form input[name="btc"]')).to_be_focused()
    page.keyboard.press('Escape')
    expect(page.locator('#trade-popup')).to_be_hidden()
    expect(page.locator('.hero [data-open-popup]')).to_be_focused()

    # Same from a row's edit button
    show_ledger(page)
    edit = page.locator(f'#transactions-body tr[data-id="{trade_id}"] .edit-button')
    edit.focus()
    page.keyboard.press('Enter')
    expect(page.locator('#trade-popup')).to_be_visible()
    page.keyboard.press('Escape')
    expect(edit).to_be_focused()

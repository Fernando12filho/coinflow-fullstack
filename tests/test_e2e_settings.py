"""Browser tests for settings and formatting (PLAN.md Phase 7.2 + 7.4).

Fake exchange rates (e2e_support): 1 USD = R$5. Live BTC price $50,000 = R$250,000.
"""
import pytest

from e2e_support import (add_trade, base_url, browser, days_ago, expect, open_dashboard,  # noqa: F401
                         page, sign_in)

pytestmark = pytest.mark.e2e


def text(page, selector):
    """Visible text with non-breaking spaces (used by Intl formatting) turned into spaces"""
    return page.locator(selector).first.inner_text().replace(' ', ' ').replace(' ', ' ')


def settings(page, base_url, **values):
    response = page.request.put(f'{base_url}/api/settings', data=values)
    assert response.ok, response.text()


def test_settings_page_saves(page, base_url):
    sign_in(page, base_url)
    page.goto(f'{base_url}/settings')
    page.select_option('select[name="currency"]', 'BRL')
    page.check('input[name="btc_unit"][value="sats"]')
    page.select_option('select[name="locale"]', 'pt-BR')
    page.click('#settings-form button[type="submit"]')
    expect(page.locator('.swal2-title')).to_have_text('Settings saved')

    page.reload()
    expect(page.locator('select[name="currency"]')).to_have_value('BRL')
    expect(page.locator('input[name="btc_unit"][value="sats"]')).to_be_checked()
    expect(page.locator('select[name="locale"]')).to_have_value('pt-BR')


def test_dashboard_in_reais_portuguese_and_sats(page, base_url):
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000')   # $30,000 = R$150,000
    settings(page, base_url, currency='BRL', locale='pt-BR', btc_unit='sats')
    page.goto(f'{base_url}/')
    expect(page.locator('#btc-price span')).not_to_have_text('--')

    assert text(page, '#btc-price span') == 'R$ 250.000,00'
    assert text(page, '#stat-break-even') == 'R$ 150.000,00'
    page.click('[data-toggle="total-btc"]')
    assert text(page, '[data-value-id="total-btc"]') == '100.000.000 sats'

    page.click('#tab-transactions-button')
    row = page.locator('#transactions-body tr').first
    expect(row).to_contain_text('1 de jan. de 2024')
    assert text(page, '#transactions-body tr td.num') == '+100.000.000 sats'


def test_editing_a_dollar_trade_while_showing_reais(page, base_url):
    sign_in(page, base_url)
    trade_id = add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000', fee='10')
    settings(page, base_url, currency='BRL')
    page.goto(f'{base_url}/')
    page.click('#tab-transactions-button')
    page.click(f'#transactions-body tr[data-id="{trade_id}"] .edit-button')

    # The form shows what was entered, in the trade's own currency, named by its code
    expect(page.locator('#fiat-label')).to_have_text('Amount paid (USD)')
    expect(page.locator('#trade-form input[name="fiat"]')).to_have_value('30000')
    expect(page.locator('#trade-form input[name="fee"]')).to_have_value('10')
    page.click('#trade-form button[type="submit"]')
    expect(page.locator('#trade-popup')).to_be_hidden()

    trade = page.request.get(f'{base_url}/api/trades').json()['trades'][0]
    assert (trade['trade_currency'], trade['trade_fiat']) == ('USD', '30000')


def test_new_trade_uses_the_display_currency(page, base_url):
    sign_in(page, base_url)
    settings(page, base_url, currency='BRL')
    page.goto(f'{base_url}/')
    page.click('.hero [data-open-popup]')
    expect(page.locator('#fiat-label')).to_have_text('Amount paid (R$)')
    page.fill('#trade-form input[name="date"]', days_ago(10))
    page.fill('#trade-form input[name="btc"]', '0.1')
    page.fill('#trade-form input[name="fiat"]', '20000')
    page.click('#trade-form button[type="submit"]')
    expect(page.locator('#trade-popup')).to_be_hidden()

    trade = page.request.get(f'{base_url}/api/trades').json()['trades'][0]
    assert (trade['trade_currency'], trade['trade_fiat']) == ('BRL', '20000')


def test_export_and_delete_from_the_settings_page(page, base_url):
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000', notes='first')
    page.goto(f'{base_url}/settings')

    with page.expect_download() as download:
        page.click('#export-link')
    assert download.value.suggested_filename.startswith('coinflow-trades-')
    content = open(download.value.path(), encoding='utf-8').read()
    assert '2024-01-01 00:00:00,buy,1,30000,USD' in content

    page.fill('#delete-data-form input[name="confirm"]', 'DELETE')
    page.click('#delete-data-form button[type="submit"]')
    page.click('.swal2-confirm')
    expect(page.locator('.swal2-title')).to_have_text('Deleted 1 trade and 0 imports')
    assert page.request.get(f'{base_url}/api/trades').json()['trades'] == []
    expect(page.locator('#delete-data-form input[name="confirm"]')).to_have_value('')

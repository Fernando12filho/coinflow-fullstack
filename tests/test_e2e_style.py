"""Browser checks for the button style override: no borders and no shadows on buttons."""
import pytest

from e2e_support import add_trade, base_url, browser, expect, open_dashboard, page, sign_in  # noqa: F401

pytestmark = pytest.mark.e2e


def border_and_shadow(page, selector):
    return page.locator(selector).first.evaluate(
        "el => { const s = getComputedStyle(el); return [s.borderTopWidth, s.borderBottomWidth, s.boxShadow]; }")


def assert_flat(page, selector):
    assert border_and_shadow(page, selector) == ['0px', '0px', 'none'], selector


def test_buttons_have_no_borders_or_shadows(page, base_url):
    page.goto(f'{base_url}/auth/login')
    assert_flat(page, '.auth-form button[type="submit"]')

    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date='2024-01-01', btc='1', fiat='30000')
    open_dashboard(page, base_url)
    for selector in ('.hero [data-open-popup]', '.nav .pill.active', '.nav a.pill:not(.active)', '.logout-button'):
        assert_flat(page, selector)

    page.click('#tab-transactions-button')
    expect(page.locator('#transactions-body tr')).to_have_count(1)
    assert_flat(page, '.edit-button')
    assert_flat(page, '.delete-button')

    page.click('.hero [data-open-popup]')
    assert_flat(page, '.close-button')
    assert_flat(page, '#trade-form button[type="submit"]')
    page.keyboard.press('Escape')

    page.click('.delete-button')
    expect(page.locator('.swal2-confirm')).to_be_visible()
    assert_flat(page, '.swal2-confirm')
    assert_flat(page, '.swal2-cancel')

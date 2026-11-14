"""Browser tests for the price chart and today's change (PLAN.md Phase 6c-d).

The fake price history (e2e_support.fake_closes) covers the last 400 finished days,
rising $25 a day to $40,000 yesterday. The live price is $50,000.
"""
import pytest

from e2e_support import add_trade, base_url, browser, days_ago, expect, page, sign_in, utc_today  # noqa: F401
from app import prices

pytestmark = pytest.mark.e2e


def chart_state(page):
    expect(page.locator('#price-chart canvas').first).to_be_visible()
    page.wait_for_function("typeof PriceChart !== 'undefined' && PriceChart.state().points > 0")
    return page.evaluate('PriceChart.state()')


def seed(page, base_url):
    # Buy 0.5 BTC for $15,000; sell 0.1 for $4,000; earn 0.001.
    # Break-even: 30,000 -> (15000 - 4000) / 0.4 = 27,500 -> 11000 / 0.401 = 27,431.42
    sign_in(page, base_url)
    add_trade(page, base_url, side='buy', date=days_ago(200), btc='0.5', fiat='15000')
    add_trade(page, base_url, side='sell', date=days_ago(50), btc='0.1', fiat='4000')
    add_trade(page, base_url, side='reward', date=days_ago(20), btc='0.001')
    page.goto(f'{base_url}/')


def test_chart_draws_price_break_even_and_trades(page, base_url):
    seed(page, base_url)
    state = chart_state(page)
    assert state['points'] == 401                      # 400 finished days + today's live price
    assert state['lastDate'] == utc_today().isoformat()
    assert state['lastPrice'] == 50000
    assert [m['side'] for m in state['markers']] == ['buy', 'sell', 'reward']
    assert [m['time'] for m in state['markers']] == [days_ago(200), days_ago(50), days_ago(20)]

    steps = state['breakEven']
    assert [round(s['value'], 2) for s in steps] == [30000, 27500, 27431.42, 27431.42]
    assert steps[-1]['time'] == utc_today().isoformat()   # extends to today
    assert state['range'] == '1Y'
    expect(page.locator('[data-range="1Y"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('#chart-empty')).to_be_hidden()


def test_range_buttons_and_trade_toggle(page, base_url):
    seed(page, base_url)
    chart_state(page)

    page.click('[data-range="3M"]')
    expect(page.locator('[data-range="3M"]')).to_have_attribute('aria-pressed', 'true')
    expect(page.locator('[data-range="1Y"]')).to_have_attribute('aria-pressed', 'false')
    state = page.evaluate('PriceChart.state()')
    assert (state['range'], state['rangeFrom']) == ('3M', days_ago(90))

    page.click('[data-range="ALL"]')
    assert page.evaluate('PriceChart.state()')['range'] == 'ALL'

    page.uncheck('#show-trades')
    assert page.evaluate('PriceChart.state()')['markers'] == []
    page.check('#show-trades')
    assert len(page.evaluate('PriceChart.state()')['markers']) == 3


def test_chart_explains_when_history_is_unavailable(page, base_url, monkeypatch):
    def down(start, end):
        raise prices.PriceHistoryError('down')

    monkeypatch.setattr(prices, 'fetch_closes', down)
    sign_in(page, base_url)
    page.goto(f'{base_url}/')
    expect(page.locator('#chart-empty')).to_be_visible()
    expect(page.locator('#price-chart')).to_be_hidden()
    expect(page.locator('#day-change')).to_be_hidden()


def test_todays_change_in_the_hero(page, base_url):
    # $50,000 now vs $40,000 at yesterday's close
    sign_in(page, base_url)
    page.goto(f'{base_url}/')
    expect(page.locator('#day-change span')).to_have_text('+25.00%')
    expect(page.locator('#day-change')).to_have_class('hero-sub profit')

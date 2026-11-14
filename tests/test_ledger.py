"""Unit tests for the calculation engine (PLAN.md Phase 2).

Every expected number below is worked out by hand in the comment next to it.
"""
from datetime import datetime
from decimal import Decimal as D

import pytest
from hypothesis import given, settings, strategies as st

from app.ledger import BUY, REWARD, SELL, LedgerError, Trade, run_ledger, valuation


def day(n):
    return datetime(2024, 1, n)


def buy(n, btc, fiat, fee='0', fee_asset='USD', **kw):
    return Trade(BUY, day(n), D(btc), D(fiat), D(fee), fee_asset, **kw)


def sell(n, btc, fiat, fee='0', fee_asset='USD', **kw):
    return Trade(SELL, day(n), D(btc), D(fiat), D(fee), fee_asset, **kw)


def reward(n, btc, **kw):
    return Trade(REWARD, day(n), D(btc), D('0'), **kw)


# ---------- Trade validation ----------

@pytest.mark.parametrize('kwargs, message', [
    ({'side': 'gift'}, 'side'),
    ({'btc': D('0')}, 'BTC amount'),
    ({'btc': D('-1')}, 'BTC amount'),
    ({'fiat': D('0')}, 'fiat amount'),
    ({'fiat': D('-5')}, 'fiat amount'),
    ({'fee': D('-1')}, 'Fee'),
    ({'fee_asset': 'EUR'}, 'Fee'),
])
def test_invalid_trades_are_rejected(kwargs, message):
    fields = dict(side=BUY, date=day(1), btc=D('1'), fiat=D('100'), fee=D('1'), fee_asset='USD')
    fields.update(kwargs)
    with pytest.raises(ValueError, match=message):
        Trade(**fields)


def test_reward_must_have_no_fiat():
    with pytest.raises(ValueError, match='fiat amount'):
        Trade(REWARD, day(1), D('0.01'), D('5'))


def test_amounts_must_be_decimal():
    with pytest.raises(TypeError):
        Trade(BUY, day(1), 0.1, D('100'))


# ---------- Position ----------

def test_empty_ledger():
    rows, pos = run_ledger([])
    assert rows == []
    assert pos.held == 0
    assert pos.break_even is None
    assert pos.average_cost is None


def test_single_buy_with_fiat_fee():
    # 0.5 BTC for $20,000 + $10 fee -> cost $20,010 -> $40,020 per BTC
    _, pos = run_ledger([buy(1, '0.5', '20000', '10')])
    assert pos.held == D('0.5')
    assert pos.invested == D('20010')
    assert pos.fees == D('10')
    assert pos.break_even == D('40020')
    assert pos.average_cost == D('40020')


def test_two_buys_average_out():
    # 1 BTC @ $100 + 1 BTC @ $300 -> $400 / 2 BTC = $200
    _, pos = run_ledger([buy(1, '1', '100'), buy(2, '1', '300')])
    assert pos.break_even == D('200')
    assert pos.average_cost == D('200')
    assert pos.buys == 2


def test_decimal_math_is_exact():
    # Three buys of 0.1 BTC: floats would give 0.30000000000000004
    _, pos = run_ledger([buy(1, '0.1', '10'), buy(2, '0.1', '10'), buy(3, '0.1', '10')])
    assert pos.held == D('0.3')


def test_partial_sell_splits_realized_and_unrealized():
    # Buy 1 BTC for $100. Sell 0.5 BTC for $100 (at $200/BTC).
    # Break-even: (100 invested - 100 proceeds) / 0.5 held = $0
    # Average cost stays $100. Realized: 100 - 0.5 * 100 = $50. Cost basis left: $50.
    rows, pos = run_ledger([buy(1, '1', '100'), sell(2, '0.5', '100')])
    assert pos.held == D('0.5')
    assert pos.proceeds == D('100')
    assert pos.break_even == D('0')
    assert pos.average_cost == D('100')
    assert pos.cost_basis == D('50')
    assert pos.realized_pnl == D('50')
    assert rows[1].realized_pnl == D('50')
    assert rows[0].realized_pnl is None

    # At $200: value $100. Total = 100 + 100 - 100 = $100 = realized 50 + unrealized 50
    v = valuation(pos, D('200'))
    assert v.value == D('100')
    assert v.total_pnl == D('100')
    assert v.unrealized_pnl == D('50')
    assert v.realized_pnl + v.unrealized_pnl == v.total_pnl


def test_sell_with_fiat_fee_reduces_proceeds():
    # Sell 0.5 BTC for $100 with a $2 fee -> $98 proceeds; realized 98 - 50 = $48
    _, pos = run_ledger([buy(1, '1', '100'), sell(2, '0.5', '100', '2')])
    assert pos.proceeds == D('98')
    assert pos.fees == D('2')
    assert pos.realized_pnl == D('48')


def test_buy_with_btc_fee_reduces_holdings():
    # Pay $1,000 for 0.01 BTC, exchange keeps 0.0001 BTC as fee -> hold 0.0099
    # Fee valued at the trade price: 0.0001 * (1000 / 0.01) = $10
    _, pos = run_ledger([buy(1, '0.01', '1000', '0.0001', 'BTC')])
    assert pos.held == D('0.0099')
    assert pos.invested == D('1000')
    assert pos.fees == D('10')
    assert pos.break_even == D('1000') / D('0.0099')


def test_sell_with_btc_fee_takes_extra_btc():
    # Hold 1 BTC. Sell 0.4 BTC for $80 and pay 0.01 BTC fee -> 0.59 BTC left
    _, pos = run_ledger([buy(1, '1', '100'), sell(2, '0.4', '80', '0.01', 'BTC')])
    assert pos.held == D('0.59')
    # 0.41 BTC left the account at $100 average cost -> realized 80 - 41 = $39
    assert pos.realized_pnl == D('39')


def test_reward_is_free_btc():
    # Buy 1 BTC for $100, earn 0.25 BTC -> 1.25 BTC for $100 = $80 per BTC
    _, pos = run_ledger([buy(1, '1', '100'), reward(2, '0.25')])
    assert pos.held == D('1.25')
    assert pos.invested == D('100')
    assert pos.break_even == D('80')
    assert pos.average_cost == D('80')
    assert pos.rewards == 1


def test_break_even_goes_negative_after_taking_out_more_than_invested():
    # Buy 1 BTC for $100, sell 0.5 for $300 -> (100 - 300) / 0.5 = -$400
    # Negative break-even means the rest is "free": even at $0 you're up overall.
    _, pos = run_ledger([buy(1, '1', '100'), sell(2, '0.5', '300')])
    assert pos.break_even == D('-400')


def test_selling_everything_closes_the_position():
    _, pos = run_ledger([buy(1, '1', '100'), sell(2, '1', '150')])
    assert pos.held == 0
    assert pos.break_even is None
    assert pos.average_cost is None
    assert pos.cost_basis == 0
    assert pos.realized_pnl == D('50')
    v = valuation(pos, D('999'))
    assert v.unrealized_pnl == 0
    assert v.total_pnl == D('50')


def test_cannot_sell_more_than_held():
    with pytest.raises(LedgerError, match='2024-01-02'):
        run_ledger([buy(1, '0.5', '100'), sell(2, '0.6', '200')])


def test_btc_fee_counts_toward_balance_check():
    with pytest.raises(LedgerError):
        run_ledger([buy(1, '1', '100'), sell(2, '1', '200', '0.001', 'BTC')])


def test_trades_are_sorted_by_date_keeping_ties_in_order():
    trades = [sell(3, '1', '200'), buy(1, '1', '100', id=1), buy(1, '1', '300', id=2)]
    rows, _ = run_ledger(trades)
    assert [r.trade.date.day for r in rows] == [1, 1, 3]
    assert [r.trade.id for r in rows[:2]] == [1, 2]


def test_running_values_per_row():
    rows, _ = run_ledger([buy(1, '1', '100'), buy(2, '1', '300'), sell(3, '1', '400')])
    assert [r.held for r in rows] == [D('1'), D('2'), D('1')]
    assert [r.break_even for r in rows] == [D('100'), D('200'), D('0')]
    assert [r.average_cost for r in rows] == [D('100'), D('200'), D('200')]
    assert rows[2].realized_pnl == D('200')  # 400 - 1 * 200


def test_mixed_currencies_are_rejected():
    with pytest.raises(LedgerError, match='currenc'):
        run_ledger([buy(1, '1', '100', currency='USD'), buy(2, '1', '100', currency='EUR', fee_asset='EUR')])


# ---------- Valuation ----------

def test_valuation_without_price():
    _, pos = run_ledger([buy(1, '1', '100')])
    v = valuation(pos, None)
    assert v.value is None
    assert v.total_pnl is None
    assert v.unrealized_pnl is None
    assert v.realized_pnl == 0


def test_valuation_percentages():
    # $100 invested, worth $150 -> +50% total, +50% unrealized
    _, pos = run_ledger([buy(1, '1', '100')])
    v = valuation(pos, D('150'))
    assert v.total_pnl_percent == D('50')
    assert v.unrealized_pnl_percent == D('50')


def test_valuation_percentages_with_nothing_invested():
    _, pos = run_ledger([reward(1, '0.1')])
    v = valuation(pos, D('1000'))
    assert v.total_pnl == D('100')
    assert v.total_pnl_percent is None
    assert v.unrealized_pnl_percent is None


# ---------- Properties that must hold for any valid history ----------

amounts = st.decimals(min_value='0.00000001', max_value='10', places=8)
prices = st.decimals(min_value='1', max_value='200000', places=2)


@st.composite
def histories(draw):
    trades, held = [], D('0')
    for n in range(draw(st.integers(1, 12))):
        kind = draw(st.sampled_from([BUY, BUY, SELL, REWARD]))
        btc = draw(amounts)
        if kind == SELL:
            if held == 0:
                continue
            btc = min(btc, held)
            held -= btc
        else:
            held += btc
        fiat = D('0') if kind == REWARD else (btc * draw(prices)).quantize(D('0.01')) or D('0.01')
        trades.append(Trade(kind, datetime(2024, 1, 1 + n), btc, fiat))
    return trades


@settings(max_examples=200, deadline=None)
@given(histories(), prices)
def test_realized_plus_unrealized_equals_total(trades, price):
    rows, pos = run_ledger(trades)
    v = valuation(pos, price)
    assert abs((v.realized_pnl + v.unrealized_pnl) - v.total_pnl) < D('0.000001')
    assert pos.held == sum((r.trade.btc if r.trade.side != SELL else -r.trade.btc) for r in rows)
    if pos.held > 0:
        # Selling everything at break-even leaves total P&L at zero
        at_bep = valuation(pos, pos.break_even)
        assert abs(at_bep.total_pnl) < D('0.000001')


def test_btc_fee_cannot_eat_the_whole_buy():
    with pytest.raises(LedgerError, match='larger than the BTC received'):
        run_ledger([buy(1, '0.001', '100', '0.001', 'BTC')])

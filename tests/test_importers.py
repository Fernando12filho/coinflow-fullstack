"""Tests for the CSV parsers (PLAN.md Phase 5).

The fixtures in tests/fixtures/ are written by hand to follow each exchange's
export format; every expected number below comes straight from those rows.
"""
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.importers import ImportFormatError, detect_provider, parse_file
from app.ledger import BTC, BUY, REWARD, SELL, run_ledger

FIXTURES = Path(__file__).parent / 'fixtures'


def load(name):
    return (FIXTURES / name).read_bytes()


def summary(parsed):
    """(side, date, btc, fiat, fee, fee_asset) for each imported trade"""
    return [(t.trade.side, t.trade.date, t.trade.btc, t.trade.fiat, t.trade.fee, t.trade.fee_asset)
            for t in parsed.trades]


# ---------- Detection ----------

@pytest.mark.parametrize('name, provider', [
    ('kraken/ledgers.csv', 'kraken'),
    ('kraken/ledgers_legacy.csv', 'kraken'),
])
def test_detect_provider(name, provider):
    assert detect_provider(load(name)) == provider


@pytest.mark.parametrize('content', [
    b'',
    b'date,amount\n2024-01-01,5\n',
    b'\x00\x01\x02 not a csv',
])
def test_unrecognised_files_are_rejected(content):
    with pytest.raises(ImportFormatError, match='Kraken or Coinbase'):
        parse_file(content)


def test_byte_order_mark_is_ignored():
    assert detect_provider(b'\xef\xbb\xbf' + load('kraken/ledgers.csv')) == 'kraken'


# ---------- Kraken ledger ----------

def test_kraken_ledger_trades():
    parsed = parse_file(load('kraken/ledgers.csv'))
    assert parsed.provider == 'kraken'
    assert summary(parsed) == [
        # trade: $500 + $1.30 fee on the USD row -> 0.012 BTC
        (BUY, datetime(2024, 1, 5, 14, 3, 21), D('0.012'), D('500'), D('1.3'), 'USD'),
        # trade with the fee taken in BTC on the BTC row
        (BUY, datetime(2024, 2, 10, 10, 0, 0), D('0.007'), D('300'), D('0.000014'), BTC),
        # "Buy Crypto": spend + receive rows sharing a refid; time is the earlier row
        (BUY, datetime(2024, 3, 1, 12, 0, 0), D('0.0015'), D('97'), D('3'), 'USD'),
        # earn / reward
        (REWARD, datetime(2024, 3, 8, 0, 10, 0), D('0.000021'), D('0'), D('0'), BTC),
        # sale: BTC row negative, USD row positive with the fee
        (SELL, datetime(2024, 5, 20, 16, 45, 0), D('0.005'), D('350'), D('0.91'), 'USD'),
        # BTC bought with euros (Phase 7): kept in EUR, fee in EUR
        (BUY, datetime(2024, 6, 1, 10, 0, 0), D('0.003'), D('200'), D('0.5'), 'EUR'),
    ]
    assert [t.trade.currency for t in parsed.trades] == ['USD'] * 5 + ['EUR']


def test_kraken_skipped_rows_are_explained():
    parsed = parse_file(load('kraken/ledgers.csv'))
    reasons = {s.line: s.reason for s in parsed.skipped}
    assert reasons == {
        2: 'Deposit (moving money in or out of Kraken does not change what you paid for BTC)',
        10: 'Earn allocation (moving BTC between your own Kraken balances)',
        11: 'Earn allocation (moving BTC between your own Kraken balances)',
        12: 'Withdrawal (moving money in or out of Kraken does not change what you paid for BTC)',
    }


def test_kraken_trades_form_a_valid_history():
    # The withdrawal is skipped, so the 0.005 BTC sale is covered by the earlier buys
    # 0.012 + (0.007 - 0.000014) + 0.0015 + 0.000021 - 0.005 + 0.003
    trades = parse_file(load('kraken/ledgers.csv')).trades
    from app.portfolio import check_history
    check_history([t.trade for t in trades])  # mixed currencies are fine for the BTC balance check
    assert sum(t.trade.btc - t.trade.fee_btc if t.trade.side != SELL else -t.trade.btc for t in trades) == D('0.018507')


def test_kraken_legacy_format():
    parsed = parse_file(load('kraken/ledgers_legacy.csv'))
    assert summary(parsed) == [
        (BUY, datetime(2022, 11, 20, 18, 22, 5), D('0.06'), D('1000'), D('2.6'), 'USD'),
        (REWARD, datetime(2022, 12, 8, 2, 0, 0), D('0.000015'), D('0'), D('0'), BTC),
    ]
    assert [s.line for s in parsed.skipped] == [4, 5]  # staking transfer between own balances


def test_kraken_trade_ids_identify_trades():
    first = parse_file(load('kraken/ledgers.csv')).trades
    again = parse_file(load('kraken/ledgers.csv')).trades
    hashes = [t.trade_hash for t in first]
    assert len(set(hashes)) == len(hashes)                  # unique within a file
    assert hashes == [t.trade_hash for t in again]           # stable across files


def test_kraken_trade_missing_a_side_is_skipped():
    content = load('kraken/ledgers.csv').decode().splitlines()
    one_leg = '\n'.join([content[0], content[2]]) + '\n'   # only the USD row of TTRADE1
    parsed = parse_file(one_leg.encode())
    assert parsed.trades == []
    assert parsed.skipped[0].reason == 'Incomplete trade: the BTC side is missing from this file'


def test_kraken_bad_number_is_reported():
    content = load('kraken/ledgers_legacy.csv').decode().replace('-1000.0000', 'abc')
    with pytest.raises(ImportFormatError, match='line 2'):
        parse_file(content.encode())


KRAKEN_HEADER = '"txid","refid","time","type","subtype","aclass","asset","amount","fee","balance"\n'


def kraken(*rows):
    return (KRAKEN_HEADER + '\n'.join(rows) + '\n').encode()


def test_kraken_edge_cases():
    parsed = parse_file(kraken(
        # line 2-3: fee on both sides -> one USD fee: 2 + 0.0001 BTC at $50,000 = $7
        '"L1","T1","2024-01-01 10:00:00","trade","","currency","USD",-500.0000,2.0000,0',
        '"L2","T1","2024-01-01 10:00:00","trade","","currency","BTC",0.0100000000,0.0001000000,0',
        '',
        # line 5: margin entries aren't trades
        '"L3","M1","2024-01-02 10:00:00","margin","","currency","USD",-5.0000,0.0000,0',
        # line 6-7: cancelled trade, amounts cancel out
        '"L4","T2","2024-01-03 10:00:00","trade","","currency","BTC",0.0100000000,0,0',
        '"L5","T2","2024-01-03 10:00:00","trade","","currency","BTC",-0.0100000000,0,0',
        # line 8: BTC side only
        '"L6","T3","2024-01-04 10:00:00","trade","","currency","XXBT",0.0100000000,0,0',
        # line 9-10: currency exchange without BTC
        '"L7","T4","2024-01-05 10:00:00","trade","","currency","ZEUR",-100.0000,0,0',
        '"L8","T4","2024-01-05 10:00:00","trade","","currency","ZUSD",108.0000,0,0',
        # line 11-12: both sides positive
        '"L9","T5","2024-01-06 10:00:00","trade","","currency","USD",100.0000,0,0',
        '"L10","T5","2024-01-06 10:00:00","trade","","currency","BTC",0.0010000000,0,0',
        # line 13-14: BTC/JPY isn't supported
        '"L11","T6","2024-01-07 10:00:00","trade","","currency","JPY",-100000,0,0',
        '"L12","T6","2024-01-07 10:00:00","trade","","currency","BTC",0.0100000000,0,0',
    ))
    assert summary(parsed) == [(BUY, datetime(2024, 1, 1, 10), D('0.01'), D('500'), D('7'), 'USD')]
    assert {s.line: s.reason for s in parsed.skipped} == {
        5: '"margin" entries are not trades',
        6: 'Cancelled trade (the amounts cancel out)',
        7: 'Cancelled trade (the amounts cancel out)',
        8: 'Incomplete trade: the USD side is missing from this file',
        9: 'EUR/USD trade without BTC',
        10: 'EUR/USD trade without BTC',
        11: 'Trade with an unexpected direction',
        12: 'Trade with an unexpected direction',
        13: 'BTC/JPY trade: only USD, EUR, GBP and BRL are supported',
        14: 'BTC/JPY trade: only USD, EUR, GBP and BRL are supported',
    }


def test_kraken_bad_date_is_reported():
    with pytest.raises(ImportFormatError, match='line 2.*not a date'):
        parse_file(kraken('"L1","T1","yesterday","trade","","currency","USD",-5,0,0'))


# ---------- Coinbase transaction history ----------

@pytest.mark.parametrize('name', ['coinbase/transactions.csv', 'coinbase/transactions_legacy.csv'])
def test_detect_coinbase(name):
    assert detect_provider(load(name)) == 'coinbase'


def test_coinbase_trades():
    parsed = parse_file(load('coinbase/transactions.csv'))
    assert parsed.provider == 'coinbase'
    assert summary(parsed) == [
        # Subtotal is what the BTC cost; the fee is separate
        (BUY, datetime(2024, 1, 15, 10, 30), D('0.002'), D('85.00'), D('1.99'), 'USD'),
        (BUY, datetime(2024, 2, 1, 8, 0), D('0.01'), D('430.00'), D('0.86'), 'USD'),
        (REWARD, datetime(2024, 2, 20, 12, 0), D('0.00001'), D('0'), D('0'), 'USD'),
        # A sale's quantity is negative in this layout; Subtotal is before the fee
        (SELL, datetime(2024, 4, 10, 9, 15), D('0.004'), D('280.00'), D('4.15'), 'USD'),
        # Priced in euros (Phase 7): kept in EUR
        (BUY, datetime(2024, 5, 4, 13, 0), D('0.001'), D('56.00'), D('1.49'), 'EUR'),
    ]
    assert parsed.trades[-1].trade.currency == 'EUR'
    assert parsed.trades[0].notes == 'Bought 0.002 BTC for $86.99 USD'


def test_coinbase_skipped_rows_are_explained():
    parsed = parse_file(load('coinbase/transactions.csv'))
    assert {s.line: s.reason for s in parsed.skipped} == {
        7: 'Send (moving BTC in or out of Coinbase does not change what you paid for it)',
        9: 'Convert (crypto-to-crypto conversions are not supported yet)',
        10: 'Receive (moving BTC in or out of Coinbase does not change what you paid for it)',
        11: 'ETH: only BTC is tracked',
    }


def test_coinbase_trades_form_a_valid_history():
    _, position = run_ledger([t.trade for t in parse_file(load('coinbase/transactions.csv')).trades
                              if t.trade.currency == 'USD'])
    assert position.held == D('0.008010')  # 0.002 + 0.01 + 0.00001 - 0.004 (USD trades only)


def test_coinbase_legacy_layout():
    parsed = parse_file(load('coinbase/transactions_legacy.csv'))
    assert summary(parsed) == [
        (BUY, datetime(2023, 6, 1, 14, 0), D('0.0040'), D('108.00'), D('1.99'), 'USD'),
        (REWARD, datetime(2023, 7, 1, 14, 0), D('0.00002'), D('0'), D('0'), 'USD'),
        (SELL, datetime(2023, 8, 1, 14, 0), D('0.0010'), D('29.00'), D('0.57'), 'USD'),
        # No Subtotal or fee given: the cost falls back to quantity x price = 0.001 x 29,100
        (BUY, datetime(2023, 8, 2, 14, 0), D('0.0010'), D('29.1000'), D('0'), 'USD'),
    ]


def test_coinbase_ids_identify_trades():
    trades = parse_file(load('coinbase/transactions.csv')).trades
    hashes = [t.trade_hash for t in trades]
    assert len(set(hashes)) == len(hashes)
    assert hashes == [t.trade_hash for t in parse_file(load('coinbase/transactions.csv')).trades]
    # The older layout has no ID column: the hash comes from the row's contents
    legacy = [t.trade_hash for t in parse_file(load('coinbase/transactions_legacy.csv')).trades]
    assert len(set(legacy)) == len(legacy)


def test_coinbase_bad_amount_is_reported():
    content = load('coinbase/transactions.csv').decode().replace('$85.00', 'eighty-five')
    with pytest.raises(ImportFormatError, match='line 4.*Subtotal'):
        parse_file(content.encode())


COINBASE_HEADER = ('Timestamp,Transaction Type,Asset,Quantity Transacted,Spot Price Currency,'
                   'Spot Price at Transaction,Subtotal,Total (inclusive of fees and/or spread),'
                   'Fees and/or Spread,Notes\n')


def coinbase(*rows):
    return (COINBASE_HEADER + '\n'.join(rows) + '\n').encode()


def test_coinbase_edge_cases():
    parsed = parse_file(coinbase(
        '2024-01-01T10:00:00Z,Buy,BTC,0,USD,40000,0,0,0,',            # line 2: no BTC amount
        '2024-01-02T10:00:00Z,Learning Bonus,BTC,0.001,USD,40000,,,,',  # line 3: unknown type
        '2024-01-03T10:00:00Z,Buy,BTC,0.001,USD,40000,40,41,1,café',    # line 4: imported
    ))
    assert [s.reason for s in parsed.skipped] == ['No BTC amount', '"Learning Bonus" is not a buy, sale or reward']
    assert len(parsed.trades) == 1


def test_coinbase_row_without_cost_is_reported():
    with pytest.raises(ImportFormatError, match='line 2: no Subtotal or price'):
        parse_file(coinbase('2024-01-01T10:00:00Z,Buy,BTC,0.001,USD,,,,,'))


def test_non_finite_amount_is_reported():
    with pytest.raises(ImportFormatError, match='line 2.*not a number'):
        parse_file(coinbase('2024-01-01T10:00:00Z,Buy,BTC,0.001,USD,40000,NaN,41,1,'))


def test_latin1_file_is_read():
    parsed = parse_file(coinbase('2024-01-03T10:00:00Z,Buy,BTC,0.001,USD,40000,40,41,1,café').decode().encode('latin-1'))
    assert parsed.trades[0].notes == 'café'


def test_coinbase_unsupported_currency_is_skipped():
    parsed = parse_file(coinbase('2024-01-03T10:00:00Z,Buy,BTC,0.001,JPY,6000000,6000,6100,100,'))
    assert parsed.skipped[0].reason == 'Priced in JPY: only USD, EUR, GBP and BRL are supported'
    assert parsed.trades == []


def test_coinbase_trade_in_reais():
    parsed = parse_file(coinbase('2024-01-03T10:00:00Z,Buy,BTC,0.001,BRL,250000,250,255,5,'))
    assert summary(parsed) == [(BUY, datetime(2024, 1, 3, 10, 0), D('0.001'), D('250'), D('5'), 'BRL')]

"""Kraken ledger export.

Each ledger row changes one asset's balance: amount is the change before the
fee, and the fee (in the same asset) comes off on top. A trade is two rows that
share a `refid`: one for USD and one for BTC. "Buy Crypto" purchases use a
`spend` row and a `receive` row sharing a `refid` in the same way.

Asset codes vary by export age: BTC may be XXBT, XBT or BTC; USD may be ZUSD or
USD. A suffix after a dot marks a balance type (XBT.M = staked BTC) and is ignored.
"""
from collections import OrderedDict
from decimal import Decimal

from app.importers import ImportedTrade, ParsedFile, SkippedRow, stable_hash
from app.importers.common import to_datetime, to_decimal
from app.ledger import BTC, BUY, REWARD, SELL, Trade

REQUIRED_COLUMNS = {'txid', 'refid', 'time', 'type', 'asset', 'amount', 'fee'}
TRADE_TYPES = {'trade', 'spend', 'receive'}
TRANSFER_REASON = 'moving money in or out of Kraken does not change what you paid for BTC'
INTERNAL_REASON = 'moving BTC between your own Kraken balances'
ASSET_CODES = {'XXBT': 'BTC', 'XBT': 'BTC', 'BTC': 'BTC', 'ZUSD': 'USD', 'USD': 'USD'}
ZERO = Decimal('0')


def is_header(row):
    return REQUIRED_COLUMNS <= {cell.lower() for cell in row}


def normalise_asset(code):
    base = code.upper().split('.')[0]
    if base in ASSET_CODES:
        return ASSET_CODES[base]
    return base[1:] if len(base) == 4 and base[0] in 'XZ' else base  # ZEUR -> EUR, XETH -> ETH


def parse(rows):
    from app.importers import find_header

    header_index = find_header(rows, is_header)
    columns = {name.lower(): i for i, name in enumerate(rows[header_index][1])}
    result = ParsedFile('kraken')

    entries = []
    for line, row in rows[header_index + 1:]:
        if not any(row):
            continue
        get = lambda name: row[columns[name]] if columns[name] < len(row) else ''  # noqa: E731
        entries.append({
            'line': line,
            'txid': get('txid'),
            'refid': get('refid'),
            'time': to_datetime(get('time'), line, 'time'),
            'type': get('type').lower(),
            'subtype': get('subtype').lower() if 'subtype' in columns else '',
            'asset': normalise_asset(get('asset')),
            'amount': to_decimal(get('amount'), line, 'amount') or ZERO,
            'fee': to_decimal(get('fee'), line, 'fee') or ZERO,
        })

    # Trades: group the rows of each refid together, keeping file order
    groups = OrderedDict()
    found = []  # (date, ImportedTrade) so the result is in date order
    for entry in entries:
        if entry['type'] in TRADE_TYPES:
            groups.setdefault(entry['refid'], []).append(entry)
            continue
        outcome = _single_row(entry)
        if isinstance(outcome, ImportedTrade):
            found.append(outcome)
        else:
            result.skipped.append(SkippedRow(entry['line'], outcome))

    for refid, group in groups.items():
        outcome = _trade_group(refid, group)
        if isinstance(outcome, ImportedTrade):
            found.append(outcome)
        else:
            result.skipped.extend(SkippedRow(e['line'], outcome) for e in group)

    result.trades = sorted(found, key=lambda t: (t.trade.date, t.lines))
    result.skipped.sort(key=lambda s: s.line)
    return result


def _single_row(entry):
    """A row outside a trade: a staking reward becomes a trade, anything else a skip reason"""
    kind, subtype = entry['type'], entry['subtype']
    is_reward = (kind == 'earn' and subtype == 'reward') or (kind == 'staking' and subtype in ('', 'reward'))
    if is_reward and entry['asset'] == BTC and entry['amount'] > 0:
        trade = Trade(REWARD, entry['time'], entry['amount'], ZERO, fee=entry['fee'], fee_asset=BTC,
                      currency='USD')
        return ImportedTrade(trade, stable_hash('kraken', entry['txid']), 'Kraken reward', (entry['line'],))
    if kind in ('deposit', 'withdrawal'):
        return f'{kind.capitalize()} ({TRANSFER_REASON})'
    if kind in ('earn', 'staking', 'transfer'):
        label = f'{kind.capitalize()} {subtype}'.strip() if subtype else kind.capitalize()
        return f'{label} ({INTERNAL_REASON})'
    return f'"{entry["type"]}" entries are not trades'


def _trade_group(refid, group):
    """The rows of one refid -> ImportedTrade, or the reason they were skipped"""
    totals = {}
    for e in group:
        amount, fee = totals.get(e['asset'], (ZERO, ZERO))
        totals[e['asset']] = (amount + e['amount'], fee + e['fee'])
    others = [asset for asset in totals if asset != BTC]

    if all(amount == 0 for amount, _ in totals.values()):
        return 'Cancelled trade (the amounts cancel out)'
    if BTC not in totals:
        if len(totals) == 1:
            return 'Incomplete trade: the BTC side is missing from this file'
        return f'{"/".join(sorted(totals))} trade without BTC'
    if not others:
        return 'Incomplete trade: the USD side is missing from this file'
    quote = others[0]
    if len(others) > 1 or quote != 'USD':
        return f'BTC/{quote} trade: only USD is supported for now'

    btc, btc_fee = totals[BTC]
    usd, usd_fee = totals['USD']
    if btc > 0 > usd:
        side, btc_amount, fiat = BUY, btc, -usd
    elif btc < 0 < usd:
        side, btc_amount, fiat = SELL, -btc, usd
    else:
        return 'Trade with an unexpected direction'

    # One fee asset per trade: keep a single fee as-is, value a BTC fee in USD if both exist
    if btc_fee and usd_fee:
        fee, fee_asset = usd_fee + btc_fee * (fiat / btc_amount), 'USD'
    elif btc_fee:
        fee, fee_asset = btc_fee, BTC
    else:
        fee, fee_asset = usd_fee, 'USD'

    trade = Trade(side, min(e['time'] for e in group), btc_amount, fiat, fee=fee, fee_asset=fee_asset,
                  currency='USD')
    return ImportedTrade(trade, stable_hash('kraken', refid), '', tuple(e['line'] for e in group))

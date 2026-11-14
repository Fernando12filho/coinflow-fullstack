"""Coinbase transaction history export.

One row per transaction. A few lines of text come before the header row. Two
layouts are in use: the current one has an `ID` column and `Price Currency` /
`Price at Transaction`; the older one has no ID and uses `Spot Price Currency` /
`Spot Price at Transaction`. Amounts may carry a currency symbol and thousands
separators ("$1,234.56"), and a sale's quantity may be negative.

For buys and sales, `Subtotal` is the value of the BTC before fees and
`Fees and/or Spread` is the fee, which matches how CoinFlow stores a trade.
"""
from decimal import Decimal

from app.importers import ImportedTrade, ParsedFile, SkippedRow, find_header, stable_hash
from app.importers.common import to_datetime, to_decimal
from app.ledger import BTC, BUY, REWARD, SELL, Trade

REQUIRED_COLUMNS = {'timestamp', 'transaction type', 'asset', 'quantity transacted', 'fees and/or spread'}
BUY_TYPES = {'buy', 'advanced trade buy'}
SELL_TYPES = {'sell', 'advanced trade sell'}
REWARD_TYPES = {'rewards income', 'staking income', 'coinbase earn', 'learning reward', 'inflation reward'}
TRANSFER_TYPES = {'send', 'receive', 'deposit', 'withdrawal', 'pro deposit', 'pro withdrawal',
                  'exchange deposit', 'exchange withdrawal'}
TRANSFER_REASON = 'moving BTC in or out of Coinbase does not change what you paid for it'
MAX_NOTES = 500
ZERO = Decimal('0')


def is_header(row):
    return REQUIRED_COLUMNS <= {cell.lower() for cell in row}


def parse(rows):
    header_index = find_header(rows, is_header)
    header = rows[header_index][1]
    columns = {name.lower(): i for i, name in enumerate(header)}

    def column(*names):
        """First column present out of several possible names -> (index, display name)"""
        for name in names:
            if name in columns:
                return columns[name], header[columns[name]]
        return None, None

    price_col = column('price at transaction', 'spot price at transaction')
    currency_col = column('price currency', 'spot price currency')
    subtotal_col = column('subtotal')
    total_col = column('total (inclusive of fees and/or spread)')
    fee_col = column('fees and/or spread')
    notes_col = column('notes')
    id_col = column('id')

    result = ParsedFile('coinbase')
    for line, row in rows[header_index + 1:]:
        if not any(row):
            continue

        def cell(col):
            index = col[0]
            return row[index] if index is not None and index < len(row) else ''

        def amount(col):
            return to_decimal(cell(col), line, col[1]) if col[0] is not None else None

        kind = row[columns['transaction type']] if columns['transaction type'] < len(row) else ''
        asset = row[columns['asset']].upper() if columns['asset'] < len(row) else ''
        reason = _skip_reason(kind, asset, cell(currency_col).upper())
        if reason:
            result.skipped.append(SkippedRow(line, reason))
            continue

        date = to_datetime(row[columns['timestamp']], line, header[columns['timestamp']])
        quantity = abs(to_decimal(row[columns['quantity transacted']], line, 'Quantity Transacted') or ZERO)
        if quantity == 0:
            result.skipped.append(SkippedRow(line, 'No BTC amount'))
            continue

        kind = kind.lower()
        if kind in REWARD_TYPES:
            trade = Trade(REWARD, date, quantity, ZERO, currency='USD')
        else:
            fiat = amount(subtotal_col)
            if fiat is None:
                price = amount(price_col)
                if price is None:
                    raise_missing(line)
                fiat = quantity * price
            fee = abs(amount(fee_col) or ZERO)
            side = BUY if kind in BUY_TYPES else SELL
            trade = Trade(side, date, quantity, abs(fiat), fee=fee, fee_asset='USD', currency='USD')

        row_id = cell(id_col)
        trade_hash = (stable_hash('coinbase', row_id) if row_id else
                      stable_hash('coinbase', *row[:len(header)]))
        notes = cell(notes_col)[:MAX_NOTES]
        result.trades.append(ImportedTrade(trade, trade_hash, notes, (line,)))

    result.trades.sort(key=lambda t: (t.trade.date, t.lines))
    return result


def _skip_reason(kind, asset, currency):
    """Why a row isn't imported, or None if it is a BTC buy, sale or reward in USD"""
    lowered = kind.lower()
    if asset != BTC:
        return f'{asset or "Unknown asset"}: only BTC is tracked'
    if lowered in TRANSFER_TYPES:
        return f'{kind} ({TRANSFER_REASON})'
    if lowered == 'convert':
        return 'Convert (crypto-to-crypto conversions are not supported yet)'
    if lowered in REWARD_TYPES:
        return None
    if lowered not in BUY_TYPES | SELL_TYPES:
        return f'"{kind}" is not a buy, sale or reward'
    if currency and currency != 'USD':
        return f'Priced in {currency}: only USD is supported for now'
    return None


def raise_missing(line):
    from app.importers import ImportFormatError
    raise ImportFormatError(f'line {line}: no Subtotal or price, so the cost of this trade is unknown')

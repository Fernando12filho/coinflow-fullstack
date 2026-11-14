"""Read exchange CSV exports into ledger trades.

Pure Python, no Flask. Supported formats:

- Kraken ledger export (current and older column layouts)
- Coinbase transaction history (current and older column layouts)

Only BTC bought, sold or earned against USD becomes a trade. Everything else
(deposits, withdrawals, transfers between your own balances, other coins, other
currencies) is reported as a skipped row with the reason, so nothing disappears
silently. Moving your own BTC around doesn't change what you paid for it, so
skipping transfers keeps the break-even price correct.
"""
import csv
import hashlib
import io
from dataclasses import dataclass, field

from app.ledger import Trade

MAX_HEADER_SCAN_LINES = 20  # Coinbase puts a few lines of text above the header


class ImportFormatError(ValueError):
    """The file isn't a supported export, or a row can't be read"""


@dataclass(frozen=True)
class ImportedTrade:
    trade: Trade
    trade_hash: str     # stable id used to skip trades that were already imported
    notes: str = ''
    lines: tuple = ()   # CSV line numbers this trade came from


@dataclass(frozen=True)
class SkippedRow:
    line: int
    reason: str


@dataclass
class ParsedFile:
    provider: str
    trades: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


def decode(content):
    """Bytes -> text, dropping a byte-order mark. Falls back to Latin-1."""
    if isinstance(content, str):
        return content.lstrip('﻿')
    try:
        return content.decode('utf-8-sig')
    except UnicodeDecodeError:
        return content.decode('latin-1')


def read_rows(text):
    """All CSV rows as lists of stripped strings, with 1-based line numbers"""
    reader = csv.reader(io.StringIO(text))
    return [(reader.line_num, [cell.strip() for cell in row]) for row in reader]


def find_header(rows, matches):
    """Index of the first row (within the scan limit) that `matches` accepts, or None"""
    for index, (_, row) in enumerate(rows[:MAX_HEADER_SCAN_LINES]):
        if matches(row):
            return index
    return None


def stable_hash(*parts):
    return hashlib.sha256('|'.join(str(p) for p in parts).encode()).hexdigest()


def detect_provider(content):
    from app.importers import coinbase, kraken

    rows = read_rows(decode(content))
    if find_header(rows, kraken.is_header) is not None:
        return 'kraken'
    if find_header(rows, coinbase.is_header) is not None:
        return 'coinbase'
    raise ImportFormatError(
        "This file isn't a Kraken or Coinbase export. Use Kraken's Ledgers CSV or Coinbase's "
        'Transaction history CSV, and upload the file unchanged.'
    )


def parse_file(content):
    """Detect the exchange and parse the file. Raises ImportFormatError."""
    from app.importers import coinbase, kraken

    try:
        provider = detect_provider(content)
    except csv.Error:
        raise ImportFormatError('This file is not a Kraken or Coinbase CSV export.') from None
    parser = {'kraken': kraken.parse, 'coinbase': coinbase.parse}[provider]
    return parser(read_rows(decode(content)))

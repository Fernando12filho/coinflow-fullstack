"""Daily BTC/USD price history, stored in the `candles` table.

History comes from Bitstamp's public OHLC API, which reaches back to August 2011
(1,000 days per request). Kraken's public OHLC API is the fallback, but it only
returns the most recent ~720 days, so it is used only when it covers the whole
range asked for; otherwise the sync waits and retries Bitstamp later, rather than
leaving a permanent hole in the history.

Only finished days are stored: today's candle is still changing. The live price
for "now" still comes from app/bitcoin.py.
"""
import calendar
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests

log = logging.getLogger(__name__)

CURRENCY = 'USD'
HISTORY_START = date(2011, 8, 18)   # first day Bitstamp has
PAGE_DAYS = 1000                    # Bitstamp's maximum per request
MAX_PAGES = 20
SYNC_RETRY_SECONDS = 600            # after a failed sync, wait this long before trying again
INSERT_BATCH = 200
TIMEOUT = 10

BITSTAMP_URL = 'https://www.bitstamp.net/api/v2/ohlc/btcusd/'
KRAKEN_URL = 'https://api.kraken.com/0/public/OHLC'

_sync_lock = threading.Lock()
_state = {'last_failure': 0.0}


class PriceHistoryError(Exception):
    """No price source could provide the requested days"""


def to_timestamp(day):
    return calendar.timegm(day.timetuple())


def from_timestamp(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).date()


# ---------- Fetching ----------

def _from_bitstamp(start, end):
    closes, cursor = [], start
    for _ in range(MAX_PAGES):
        if cursor > end:
            break
        response = requests.get(BITSTAMP_URL, params={'step': 86400, 'limit': PAGE_DAYS,
                                                      'start': to_timestamp(cursor)}, timeout=TIMEOUT)
        response.raise_for_status()
        rows = response.json()['data']['ohlc']
        page = [(from_timestamp(row['timestamp']), Decimal(row['close'])) for row in rows]
        page = [(day, close) for day, close in page if cursor <= day <= end]
        if not page:
            break
        closes.extend(page)
        cursor = page[-1][0] + timedelta(days=1)
    return closes


def _from_kraken(start, end):
    response = requests.get(KRAKEN_URL, params={'pair': 'XBTUSD', 'interval': 1440}, timeout=TIMEOUT)
    response.raise_for_status()
    body = response.json()
    if body.get('error'):
        raise PriceHistoryError(f'Kraken: {body["error"]}')
    rows = next(value for key, value in body['result'].items() if key != 'last')
    closes = [(from_timestamp(row[0]), Decimal(str(row[4]))) for row in rows]
    if not closes or closes[0][0] > start:
        raise PriceHistoryError('Kraken does not go back far enough')
    return [(day, close) for day, close in closes if start <= day <= end]


def fetch_closes(start, end):
    """Daily closes for start..end (inclusive), oldest first. Raises PriceHistoryError."""
    for name, source in (('Bitstamp', _from_bitstamp), ('Kraken', _from_kraken)):
        try:
            return source(start, end)
        except Exception as e:  # network errors, bad responses, short history
            log.warning('Price history from %s failed: %s', name, e)
    raise PriceHistoryError('No price source is available right now')


# ---------- Storage ----------

def store_closes(db, closes):
    """Insert closes; days already stored are left untouched"""
    rows = list(closes)
    for i in range(0, len(rows), INSERT_BATCH):
        batch = rows[i:i + INSERT_BATCH]
        placeholders = ', '.join(['(?, ?, ?)'] * len(batch))
        params = [value for day, close in batch for value in (CURRENCY, day.isoformat(), format(close, 'f'))]
        db.execute(f'INSERT INTO candles (currency, day, close) VALUES {placeholders} '
                   'ON CONFLICT (currency, day) DO NOTHING', params)
    db.commit()


def load_closes(db):
    rows = db.execute('SELECT day, close FROM candles WHERE currency = ? ORDER BY day', (CURRENCY,)).fetchall()
    return [(date.fromisoformat(row['day']), Decimal(row['close'])) for row in rows]


def last_stored_day(db):
    row = db.execute('SELECT MAX(day) AS day FROM candles WHERE currency = ?', (CURRENCY,)).fetchone()
    return date.fromisoformat(row['day']) if row['day'] else None


def sync(db, today=None):
    """Fetch any finished days not stored yet. Returns True if the history is up to date."""
    today = today or datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    with _sync_lock:
        last = last_stored_day(db)
        start = last + timedelta(days=1) if last else HISTORY_START
        if start > yesterday:
            return True
        if time.time() - _state['last_failure'] < SYNC_RETRY_SECONDS:
            return False
        try:
            closes = fetch_closes(start, yesterday)
        except PriceHistoryError:
            _state['last_failure'] = time.time()
            return False
        store_closes(db, closes)
        return True

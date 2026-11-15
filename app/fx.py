"""Daily exchange rates for showing amounts in USD, EUR, GBP or BRL.

Rates are the European Central Bank's daily reference rates, served by Frankfurter
(keyless, https://api.frankfurter.dev/v1/), stored in the `fx_rates` table as
"units of currency per 1 USD". One request returns every business day since 2010.

Weekends and holidays have no rate: the latest earlier rate is used, up to
LOOKBACK_DAYS back. Older gaps, or dates before the first rate, raise
RateUnavailable instead of guessing.
"""
import bisect
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import requests

log = logging.getLogger(__name__)

BASE = 'USD'
SUPPORTED = ('USD', 'EUR', 'GBP', 'BRL')
QUOTES = ('BRL', 'EUR', 'GBP')        # what we fetch against USD
RATES_START = date(2010, 1, 1)
LOOKBACK_DAYS = 10
SYNC_INTERVAL_SECONDS = 3600          # after a successful sync, don't ask again for an hour
RETRY_SECONDS = 600                   # after a failed sync, wait before trying again
INSERT_BATCH = 200
TIMEOUT = 15
URL = 'https://api.frankfurter.dev/v1/{start}..{end}'

_lock = threading.Lock()
_state = {'last_success': 0.0, 'last_failure': 0.0}


class RateUnavailable(Exception):
    """No exchange rate is known for that currency and date"""


def reset_state():
    _state.update(last_success=0.0, last_failure=0.0)


# ---------- Fetching and storage ----------

def fetch_rates(start, end):
    """[(day, currency, rate)] for business days start..end. Raises on any failure."""
    response = requests.get(URL.format(start=start.isoformat(), end=end.isoformat()),
                            params={'from': BASE, 'to': ','.join(QUOTES)}, timeout=TIMEOUT)
    response.raise_for_status()
    rows = []
    for day, values in response.json()['rates'].items():
        for currency, rate in values.items():
            if currency in QUOTES:
                rows.append((date.fromisoformat(day), currency, Decimal(str(rate))))
    return rows


def store_rates(db, rows):
    rows = list(rows)
    for i in range(0, len(rows), INSERT_BATCH):
        batch = rows[i:i + INSERT_BATCH]
        placeholders = ', '.join(['(?, ?, ?)'] * len(batch))
        params = [v for day, currency, rate in batch for v in (currency, day.isoformat(), format(rate, 'f'))]
        db.execute(f'INSERT INTO fx_rates (currency, day, rate) VALUES {placeholders} '
                   'ON CONFLICT (currency, day) DO NOTHING', params)
    db.commit()


def last_stored_day(db):
    row = db.execute('SELECT MAX(day) AS day FROM fx_rates').fetchone()
    return date.fromisoformat(row['day']) if row['day'] else None


def sync(db, today=None):
    """Fetch rates for days not stored yet. Returns True if rates are usable and current."""
    today = today or datetime.now(timezone.utc).date()
    with _lock:
        now = time.time()
        if now - _state['last_success'] < SYNC_INTERVAL_SECONDS:
            return True
        if now - _state['last_failure'] < RETRY_SECONDS:
            return False
        last = last_stored_day(db)
        start = last + timedelta(days=1) if last else RATES_START
        if start <= today:
            try:
                store_rates(db, fetch_rates(start, today))
            except Exception as e:  # network errors, bad responses
                log.warning('Exchange rates from Frankfurter failed: %s', e)
                _state['last_failure'] = now
                return False
        _state['last_success'] = now
        return True


# ---------- Converting ----------

class Converter:
    """Converts amounts between supported currencies using the stored daily rates"""

    def __init__(self, rows):
        self._days, self._rates = {}, {}
        for currency, day, rate in sorted(rows):
            self._days.setdefault(currency, []).append(day)
            self._rates.setdefault(currency, []).append(rate)

    def rate(self, currency, day):
        """Units of `currency` per 1 USD on `day` (or the latest earlier business day)"""
        if currency == BASE:
            return Decimal('1')
        days = self._days.get(currency)
        if not days:
            raise RateUnavailable(f'No exchange rate for {currency}')
        index = bisect.bisect_right(days, day) - 1
        if index < 0 or (day - days[index]).days > LOOKBACK_DAYS:
            raise RateUnavailable(f'No exchange rate for {currency} on {day.isoformat()}')
        return self._rates[currency][index]

    def convert(self, amount, from_currency, to_currency, day):
        if from_currency == to_currency:
            return amount
        return amount / self.rate(from_currency, day) * self.rate(to_currency, day)


def load_converter(db):
    rows = db.execute('SELECT currency, day, rate FROM fx_rates').fetchall()
    return Converter((row['currency'], date.fromisoformat(row['day']), Decimal(row['rate'])) for row in rows)

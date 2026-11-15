"""Trade ledger storage and API.

Routes:
    GET    /api/trades           all trades, newest first, with running values
    POST   /api/trades           add a trade
    PUT    /api/trades/<id>      replace a trade
    DELETE /api/trades/<id>      delete a trade
    GET    /api/portfolio        position summary valued at the current price
    GET    /api/trades/export    every trade as CSV, in its original currency

Every change replays the whole ledger first and is refused if it would make the
history impossible (e.g. a sale of BTC that isn't held at that date).

Trades are stored in their own currency. Responses are in the user's display
currency (Settings): each trade is converted at the exchange rate on its date, and
the live price at today's rate. The original amounts are returned alongside.
"""
import csv
import io
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from flask import Blueprint, Response, g, jsonify, request

from app.auth import login_required
from app.db import get_db
from app import fx
from app.ledger import BTC, REWARD, LedgerError, Trade, run_ledger, valuation

bp = Blueprint('portfolio', __name__, url_prefix='/api')

CURRENCY = 'USD'  # currency of the live price and of trades from before Phase 7
FX_ERROR = ("Exchange rates aren't available right now, so amounts can't be shown in {currency}. "
            'Try again in a few minutes, or switch to USD in Settings.')
MAX_BTC = Decimal('21000000')
MAX_FIAT = Decimal('1000000000000')
MAX_DECIMAL_PLACES = 8
MAX_NOTES_LENGTH = 500
OUTPUT_PRECISION = Decimal('0.00000001')


# ---------- Formatting ----------

def fmt(value):
    """Decimal -> plain string without trailing zeros or exponents ('20000', '0.5'). None stays None."""
    if value is None:
        return None
    value = value.quantize(OUTPUT_PRECISION, rounding=ROUND_HALF_EVEN) if value.as_tuple().exponent < -8 else value
    if value == 0:
        return '0'
    return format(value.normalize(), 'f')


# ---------- Parsing request bodies ----------

def parse_amount(raw, label):
    """Parse a JSON number or numeric string into a finite Decimal"""
    if raw is None or isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
        raise ValueError(f'{label} must be a number')
    try:
        value = Decimal(str(raw).strip())
    except InvalidOperation:
        raise ValueError(f'{label} must be a number') from None
    if not value.is_finite():
        raise ValueError(f'{label} must be a number')
    if value.as_tuple().exponent < -MAX_DECIMAL_PLACES:
        raise ValueError(f'{label} can have at most {MAX_DECIMAL_PLACES} decimal places')
    return value


def parse_date(raw):
    """'YYYY-MM-DD' -> datetime at midnight. Missing -> today."""
    if not raw:
        return datetime.combine(date.today(), datetime.min.time())
    try:
        parsed = date.fromisoformat(raw)
    except (TypeError, ValueError):
        raise ValueError('Invalid date, use YYYY-MM-DD') from None
    # Allow one day of slack for users in timezones ahead of the server
    if parsed > date.today() + timedelta(days=1):
        raise ValueError('Date cannot be in the future')
    return datetime.combine(parsed, datetime.min.time())


def parse_notes(raw):
    if raw is None:
        return ''
    if not isinstance(raw, str):
        raise ValueError('Notes must be text')
    notes = raw.strip()
    if len(notes) > MAX_NOTES_LENGTH:
        raise ValueError(f'Notes must be {MAX_NOTES_LENGTH} characters or fewer')
    return notes


def parse_trade(data, trade_id=None, currency=CURRENCY):
    """Turn a request body into (Trade, notes). Raises ValueError with a user-facing message.

    `currency` is used unless the body names a supported currency of its own.
    """
    side = data.get('side')
    requested = data.get('currency')
    if requested not in (None, ''):
        if requested not in fx.SUPPORTED:
            raise ValueError(f'Currency must be one of: {", ".join(fx.SUPPORTED)}')
        currency = requested
    btc = parse_amount(data.get('btc'), 'BTC amount')
    if btc > MAX_BTC:
        raise ValueError('BTC amount cannot exceed 21,000,000')

    raw_fiat = data.get('fiat')
    fiat = Decimal('0') if side == REWARD and raw_fiat in (None, '') else parse_amount(raw_fiat, 'The fiat amount')
    if fiat > MAX_FIAT:
        raise ValueError('The fiat amount is too large')

    raw_fee = data.get('fee')
    fee = Decimal('0') if raw_fee in (None, '') else parse_amount(raw_fee, 'Fee')

    trade = Trade(
        side=side,
        date=parse_date(data.get('date')),
        btc=btc,
        fiat=fiat,
        fee=fee,
        fee_asset=data.get('fee_asset') or currency,
        currency=currency,
        id=trade_id,
    )
    return trade, parse_notes(data.get('notes'))


# ---------- Storage ----------

def _as_datetime(value):
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


def row_to_trade(row):
    return Trade(
        side=row['side'],
        date=_as_datetime(row['trade_date']),
        btc=Decimal(row['btc_amount']),
        fiat=Decimal(row['fiat_amount']),
        fee=Decimal(row['fee_amount']),
        fee_asset=row['fee_asset'],
        currency=row['currency'],
        id=row['id'],
    )


def load_rows(user_id):
    """The user's trade rows in ledger order (date, then insertion order)"""
    return get_db().execute(
        'SELECT * FROM trades WHERE user_id = ? ORDER BY trade_date, id', (user_id,)
    ).fetchall()


def insert_trade(db, user_id, trade, notes, source='manual', import_id=None, trade_hash=None):
    return db.execute(
        'INSERT INTO trades (user_id, side, trade_date, btc_amount, fiat_amount, fee_amount, '
        'fee_asset, currency, source, notes, import_id, trade_hash) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id',
        (user_id, trade.side, trade.date.isoformat(' '), fmt(trade.btc), fmt(trade.fiat),
         fmt(trade.fee), trade.fee_asset, trade.currency, source, notes, import_id, trade_hash),
    ).fetchone()['id']


def check_history(trades):
    """Raise LedgerError if these trades don't form a valid history.

    Only BTC amounts decide whether a history is possible, so currencies are set
    aside here: the check works even when exchange rates are unavailable. A new
    trade (id None) goes after existing trades on the same date, matching the
    order it will have once stored.
    """
    big = float('inf')
    neutral = [replace(t, currency='XXX', fee_asset=BTC if t.fee_asset == BTC else 'XXX') for t in trades]
    run_ledger(sorted(neutral, key=lambda t: (t.date, t.id if t.id is not None else big)))


def display_currency(user_id):
    from app.settings import get_settings
    return get_settings(user_id)['currency']


def get_converter(currency, trades):
    """An fx.Converter when anything needs converting into `currency`, else None"""
    if currency == CURRENCY and all(t.currency == currency for t in trades):
        return None
    db = get_db()
    fx.sync(db)  # if this fails, stored rates are still used; missing ones raise RateUnavailable
    return fx.load_converter(db)


def convert_trade(trade, currency, converter):
    """The trade with its fiat amounts in `currency`, at the rate on the trade's date"""
    if trade.currency == currency:
        return trade
    day = trade.date.date()
    btc_fee = trade.fee_asset == BTC
    return replace(
        trade,
        fiat=converter.convert(trade.fiat, trade.currency, currency, day),
        fee=trade.fee if btc_fee else converter.convert(trade.fee, trade.currency, currency, day),
        fee_asset=BTC if btc_fee else currency,
        currency=currency,
    )


def ledger_payload(rows, currency=CURRENCY, converter=None):
    """(trade dicts newest first, Position) for the stored rows, in `currency`.

    Raises fx.RateUnavailable if a needed exchange rate is missing.
    """
    by_id = {row['id']: row for row in rows}
    originals = {row['id']: row_to_trade(row) for row in rows}
    ledger_rows, position = run_ledger([convert_trade(t, currency, converter) for t in originals.values()])
    trades = []
    for lr in reversed(ledger_rows):
        t, row, original = lr.trade, by_id[lr.trade.id], originals[lr.trade.id]
        trades.append({
            'id': t.id,
            'side': t.side,
            'date': t.date.strftime('%Y-%m-%d'),
            'btc': fmt(t.btc),
            'fiat': fmt(t.fiat),
            'price': fmt(t.price),
            'fee': fmt(t.fee),
            'fee_asset': t.fee_asset,
            'currency': t.currency,
            'notes': row['notes'] or '',
            'source': row['source'],
            'held': fmt(lr.held),
            'break_even': fmt(lr.break_even),
            'average_cost': fmt(lr.average_cost),
            'realized_pnl': fmt(lr.realized_pnl),
            'trade_currency': original.currency,
            'trade_fiat': fmt(original.fiat),
            'trade_fee': fmt(original.fee),
        })
    return trades, position


def user_ledger(user_id):
    """(trades, position, currency, converter) for the user, in their display currency"""
    rows = load_rows(user_id)
    currency = display_currency(user_id)
    converter = get_converter(currency, [row_to_trade(row) for row in rows])
    trades, position = ledger_payload(rows, currency, converter)
    return trades, position, currency, converter


def fx_unavailable(currency):
    return jsonify({'success': False, 'error': FX_ERROR.format(currency=currency)}), 503


def current_price():
    from app.bitcoin import get_bitcoin_price
    price = get_bitcoin_price()
    return Decimal(str(price)) if price else None


def portfolio_payload(position, price, currency=CURRENCY):
    v = valuation(position, price)
    return {
        'currency': currency,
        'price': fmt(price),
        'held': fmt(position.held),
        'invested': fmt(position.invested),
        'proceeds': fmt(position.proceeds),
        'fees': fmt(position.fees),
        'cost_basis': fmt(position.cost_basis),
        'break_even': fmt(position.break_even),
        'average_cost': fmt(position.average_cost),
        'realized_pnl': fmt(v.realized_pnl),
        'value': fmt(v.value),
        'total_pnl': fmt(v.total_pnl),
        'total_pnl_percent': fmt(v.total_pnl_percent),
        'unrealized_pnl': fmt(v.unrealized_pnl),
        'unrealized_pnl_percent': fmt(v.unrealized_pnl_percent),
        'buys': position.buys,
        'sells': position.sells,
        'rewards': position.rewards,
    }


def migrate_legacy_holdings(db):
    """Move rows from the pre-ledger bitcoin_holding table into trades, then drop
    the old bitcoin_holding and transaction_history tables.

    Everything happens in one transaction, so a failure leaves the old data in place.
    """
    from app.db import table_exists

    if not table_exists(db, 'bitcoin_holding'):
        if table_exists(db, 'transaction_history'):
            db.execute('DROP TABLE transaction_history')
            db.commit()
        return

    for h in db.execute('SELECT * FROM bitcoin_holding ORDER BY id').fetchall():
        btc = Decimal(str(h['amount']))
        fiat = (btc * Decimal(str(h['purchase_price']))).quantize(OUTPUT_PRECISION)
        trade = Trade('buy', _as_datetime(h['purchase_date']), btc, fiat, currency=CURRENCY)
        insert_trade(db, h['user_id'], trade, h['notes'] or '')
    db.execute('DROP TABLE bitcoin_holding')
    if table_exists(db, 'transaction_history'):
        db.execute('DROP TABLE transaction_history')
    db.commit()


# ---------- Routes ----------

def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _find_row(rows, trade_id):
    return next((row for row in rows if row['id'] == trade_id), None)


@bp.route('/trades', methods=['GET'])
@login_required
def list_trades():
    try:
        trades, _, _, _ = user_ledger(g.user['id'])
    except fx.RateUnavailable:
        return fx_unavailable(display_currency(g.user['id']))
    return jsonify({'success': True, 'trades': trades})


@bp.route('/trades', methods=['POST'])
@login_required
def create_trade():
    status, payload = save_trade(_body())
    return jsonify(payload), status


def save_trade(data, trade_id=None, source='manual'):
    """Validate and store a new trade (trade_id None) or replace an existing one.

    Returns (status, payload).
    """
    if data is None:
        return 400, {'success': False, 'error': 'Request body must be a JSON object'}

    rows = load_rows(g.user['id'])
    existing = _find_row(rows, trade_id) if trade_id is not None else None
    if trade_id is not None and existing is None:
        return 404, {'success': False, 'error': 'Trade not found'}

    # New trades are in the display currency; an edit keeps the trade's own currency
    currency = existing['currency'] if existing else display_currency(g.user['id'])
    try:
        trade, notes = parse_trade(data, trade_id, currency)
        others = [row_to_trade(row) for row in rows if row['id'] != trade_id]
        check_history(others + [trade])
    except (ValueError, LedgerError) as e:
        return 400, {'success': False, 'error': str(e)}

    db = get_db()
    if trade_id is None:
        trade_id = insert_trade(db, g.user['id'], trade, notes, source)
        status = 201
    else:
        db.execute(
            'UPDATE trades SET side = ?, trade_date = ?, btc_amount = ?, fiat_amount = ?, fee_amount = ?, '
            'fee_asset = ?, currency = ?, notes = ? WHERE id = ? AND user_id = ?',
            (trade.side, trade.date.isoformat(' '), fmt(trade.btc), fmt(trade.fiat), fmt(trade.fee),
             trade.fee_asset, trade.currency, notes, trade_id, g.user['id']),
        )
        status = 200
    db.commit()

    try:
        trades, _, _, _ = user_ledger(g.user['id'])
    except fx.RateUnavailable:  # saved; it just can't be shown converted right now
        return status, {'success': True, 'trade': {'id': trade_id}}
    return status, {'success': True, 'trade': next(t for t in trades if t['id'] == trade_id)}


@bp.route('/trades/<int:trade_id>', methods=['PUT'])
@login_required
def update_trade(trade_id):
    status, payload = save_trade(_body(), trade_id)
    return jsonify(payload), status


@bp.route('/trades/<int:trade_id>', methods=['DELETE'])
@login_required
def delete_trade(trade_id):
    status, payload = remove_trade(trade_id)
    return jsonify(payload), status


def remove_trade(trade_id):
    rows = load_rows(g.user['id'])
    if _find_row(rows, trade_id) is None:
        return 404, {'success': False, 'error': 'Trade not found'}
    try:
        check_history([row_to_trade(row) for row in rows if row['id'] != trade_id])
    except LedgerError as e:
        return 400, {'success': False, 'error': f'Deleting this trade would break your history: {e}'}

    db = get_db()
    db.execute('DELETE FROM trades WHERE id = ? AND user_id = ?', (trade_id, g.user['id']))
    db.commit()
    return 200, {'success': True}


EXPORT_COLUMNS = ['date', 'type', 'btc', 'amount', 'currency', 'fee', 'fee_currency',
                  'price_per_btc', 'source', 'notes']


def _safe_cell(text):
    """Stop spreadsheets from running a cell as a formula (CSV injection)"""
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


@bp.route('/trades/export', methods=['GET'])
@login_required
def export_trades():
    """Every trade, oldest first, with the amounts and currency it was entered in"""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(EXPORT_COLUMNS)
    for row in load_rows(g.user['id']):
        t = row_to_trade(row)
        writer.writerow([
            t.date.isoformat(' '), t.side, fmt(t.btc), fmt(t.fiat), t.currency, fmt(t.fee), t.fee_asset,
            '' if t.side == REWARD else fmt(t.price), row['source'], _safe_cell(row['notes'] or ''),
        ])
    filename = f'coinflow-trades-{date.today().isoformat()}.csv'
    return Response(out.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={filename}'})


@bp.route('/portfolio', methods=['GET'])
@login_required
def get_portfolio():
    try:
        _, position, currency, converter = user_ledger(g.user['id'])
        price = current_price()
        if price is not None and currency != CURRENCY:
            price = converter.convert(price, CURRENCY, currency, datetime.now(timezone.utc).date())
    except fx.RateUnavailable:
        return fx_unavailable(display_currency(g.user['id']))
    return jsonify({'success': True, 'portfolio': portfolio_payload(position, price, currency)})

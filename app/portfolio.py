"""Trade ledger storage and API.

Routes:
    GET    /api/trades           all trades, newest first, with running values
    POST   /api/trades           add a trade
    PUT    /api/trades/<id>      replace a trade
    DELETE /api/trades/<id>      delete a trade
    GET    /api/portfolio        position summary valued at the current price

Every change replays the whole ledger first and is refused if it would make the
history impossible (e.g. a sale of BTC that isn't held at that date).
"""
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from app.auth import login_required
from app.db import get_db
from app.ledger import BTC, REWARD, LedgerError, Trade, run_ledger, valuation

bp = Blueprint('portfolio', __name__, url_prefix='/api')

CURRENCY = 'USD'  # display currency becomes a setting in Phase 7
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


def parse_trade(data, trade_id=None):
    """Turn a request body into (Trade, notes). Raises ValueError with a user-facing message."""
    side = data.get('side')
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
        fee_asset=data.get('fee_asset') or CURRENCY,
        currency=CURRENCY,
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


def insert_trade(db, user_id, trade, notes, source='manual'):
    return db.execute(
        'INSERT INTO trades (user_id, side, trade_date, btc_amount, fiat_amount, fee_amount, '
        'fee_asset, currency, source, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id',
        (user_id, trade.side, trade.date.isoformat(' '), fmt(trade.btc), fmt(trade.fiat),
         fmt(trade.fee), trade.fee_asset, trade.currency, source, notes),
    ).fetchone()['id']


def check_history(trades):
    """Raise LedgerError if these trades don't form a valid history.

    A new trade (id None) goes after existing trades on the same date, matching
    the order it will have once stored.
    """
    big = float('inf')
    run_ledger(sorted(trades, key=lambda t: (t.date, t.id if t.id is not None else big)))


def ledger_payload(rows):
    """(trade dicts newest first, Position) for the given stored rows"""
    by_id = {row['id']: row for row in rows}
    ledger_rows, position = run_ledger([row_to_trade(row) for row in rows])
    trades = []
    for lr in reversed(ledger_rows):
        t, row = lr.trade, by_id[lr.trade.id]
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
        })
    return trades, position


def current_price():
    from app.bitcoin import get_bitcoin_price
    price = get_bitcoin_price()
    return Decimal(str(price)) if price else None


def portfolio_payload(position, price):
    v = valuation(position, price)
    return {
        'currency': position.currency or CURRENCY,
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
    """Move rows from the old bitcoin_holding table into trades as manual buys.

    Insert and delete happen in one transaction, so running this again is safe.
    """
    holdings = db.execute('SELECT * FROM bitcoin_holding ORDER BY id').fetchall()
    if not holdings:
        return
    for h in holdings:
        btc = Decimal(str(h['amount']))
        fiat = (btc * Decimal(str(h['purchase_price']))).quantize(OUTPUT_PRECISION)
        trade = Trade('buy', _as_datetime(h['purchase_date']), btc, fiat, currency=CURRENCY)
        insert_trade(db, h['user_id'], trade, h['notes'] or '')
    db.execute('DELETE FROM bitcoin_holding')
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
    trades, _ = ledger_payload(load_rows(g.user['id']))
    return jsonify({'success': True, 'trades': trades})


@bp.route('/trades', methods=['POST'])
@login_required
def create_trade():
    status, payload = save_trade(_body())
    return jsonify(payload), status


def save_trade(data, trade_id=None, source='manual'):
    """Validate and store a new trade (trade_id None) or replace an existing one.

    Returns (status, payload). Shared by the API and the old holdings endpoint.
    """
    if data is None:
        return 400, {'success': False, 'error': 'Request body must be a JSON object'}

    rows = load_rows(g.user['id'])
    if trade_id is not None and _find_row(rows, trade_id) is None:
        return 404, {'success': False, 'error': 'Trade not found'}

    try:
        trade, notes = parse_trade(data, trade_id)
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
            'fee_asset = ?, notes = ? WHERE id = ? AND user_id = ?',
            (trade.side, trade.date.isoformat(' '), fmt(trade.btc), fmt(trade.fiat), fmt(trade.fee),
             trade.fee_asset, notes, trade_id, g.user['id']),
        )
        status = 200
    db.commit()

    trades, _ = ledger_payload(load_rows(g.user['id']))
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


@bp.route('/portfolio', methods=['GET'])
@login_required
def get_portfolio():
    _, position = ledger_payload(load_rows(g.user['id']))
    return jsonify({'success': True, 'portfolio': portfolio_payload(position, current_price())})

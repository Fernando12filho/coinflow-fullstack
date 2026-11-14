import time
import requests
from flask import Blueprint, current_app, jsonify, request, g
from app.auth import login_required

bp = Blueprint('bitcoin', __name__, url_prefix='/api/bitcoin')

# Price APIs are rate limited, so reuse a recent price
PRICE_CACHE_SECONDS = 60
_price_cache = {'price': None, 'fetched_at': 0.0}


def get_bitcoin_price():
    """Return the current Bitcoin price, cached for PRICE_CACHE_SECONDS"""
    now = time.time()
    if _price_cache['price'] and now - _price_cache['fetched_at'] < PRICE_CACHE_SECONDS:
        return _price_cache['price']

    price = _fetch_bitcoin_price()
    if price:
        _price_cache.update(price=price, fetched_at=now)
        return price
    # Fall back to the last known price if every source is unavailable
    return _price_cache['price']


# Price sources, tried in order. CoinGecko's keyless API sometimes blocks
# cloud hosting IPs, so Coinbase's public endpoint is used as a fallback.
PRICE_SOURCES = [
    ('CoinGecko', 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
     lambda data: data['bitcoin']['usd']),
    ('Coinbase', 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
     lambda data: data['data']['amount']),
]


def _fetch_bitcoin_price():
    """Fetch current Bitcoin price from the first source that responds"""
    for name, url, extract in PRICE_SOURCES:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return float(extract(response.json()))
        except Exception as e:
            current_app.logger.warning('Error fetching Bitcoin price from %s: %s', name, e)
    return None


@bp.route('/price', methods=['GET'])
def get_price():
    """Get current Bitcoin price"""
    price = get_bitcoin_price()
    if price:
        return jsonify({'success': True, 'price': price})
    return jsonify({'success': False, 'error': 'Unable to fetch price'}), 500


# ---------- Old holdings endpoints ----------
# Kept so the current dashboard keeps working. They read and write the trades
# ledger (app/portfolio.py) and are removed when the Phase 4 UI replaces them.

def _float(value):
    return float(value) if value is not None else None


@bp.route('/holdings', methods=['GET'])
@login_required
def get_holdings():
    """Get user's Bitcoin holdings (buy trades) in the old response shape"""
    from app.portfolio import current_price, load_rows, row_to_trade
    from app.ledger import BUY, run_ledger, valuation

    rows = load_rows(g.user['id'])
    _, position = run_ledger([row_to_trade(row) for row in rows])
    price = current_price()

    holdings_list = []
    for row in reversed(rows):
        trade = row_to_trade(row)
        if trade.side != BUY:
            continue
        invested = trade.fiat + trade.fee_fiat
        value = trade.btc * price if price is not None else None
        profit_loss = value - invested if value is not None else None
        holdings_list.append({
            'id': trade.id,
            'amount': float(trade.btc),
            'purchase_price': float(trade.price),
            'purchase_date': trade.date,
            'invested': float(invested),
            'current_value': _float(value),
            'profit_loss': _float(profit_loss),
            'profit_loss_percent': _float(profit_loss / invested * 100) if profit_loss is not None else None,
            'notes': row['notes'] or '',
        })

    v = valuation(position, price)
    return jsonify({
        'success': True,
        'holdings': holdings_list,
        'summary': {
            'total_amount': float(position.held),
            'total_invested': float(position.invested),
            'current_value': _float(v.value),
            'current_price': _float(price),
            'total_profit_loss': _float(v.total_pnl),
            'total_profit_loss_percent': _float(v.total_pnl_percent) if v.total_pnl is not None else None,
        }
    })


@bp.route('/holdings', methods=['POST'])
@login_required
def add_holding():
    """Add a buy trade from the old (amount, purchase_price) request shape"""
    from decimal import Decimal, InvalidOperation
    from app.portfolio import OUTPUT_PRECISION, save_trade

    data = request.get_json(silent=True) or {}
    amount = data.get('amount')
    purchase_price = data.get('purchase_price')

    if not amount or not purchase_price:
        return jsonify({'success': False, 'error': 'Amount and purchase price are required'}), 400
    try:
        btc = Decimal(str(amount))
        fiat = (btc * Decimal(str(purchase_price))).quantize(OUTPUT_PRECISION)
    except InvalidOperation:
        return jsonify({'success': False, 'error': 'Invalid number format'}), 400

    status, payload = save_trade({
        'side': 'buy',
        'date': data.get('purchase_date'),
        'btc': str(btc),
        'fiat': str(fiat),
        'notes': data.get('notes'),
    })
    if payload.get('success'):
        payload = {'success': True, 'holding_id': payload['trade']['id']}
    return jsonify(payload), 201 if status == 201 else status


@bp.route('/holdings/<int:holding_id>', methods=['DELETE'])
@login_required
def delete_holding(holding_id):
    """Delete a trade. Deleting corrects a mistaken entry; it is not a sale."""
    from app.portfolio import remove_trade

    status, payload = remove_trade(holding_id)
    if status == 404:
        payload = {'success': False, 'error': 'Holding not found'}
    return jsonify(payload), status


@bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """User's trades, newest first, in the old transaction-history shape"""
    from app.portfolio import load_rows, row_to_trade

    transactions_list = []
    for row in reversed(load_rows(g.user['id'])):
        trade = row_to_trade(row)
        transactions_list.append({
            'id': trade.id,
            'type': trade.side.upper(),
            'amount': float(trade.btc),
            'price': float(trade.price),
            'total_value': float(trade.fiat),
            'date': trade.date,
        })
    return jsonify({'success': True, 'transactions': transactions_list[:50]})

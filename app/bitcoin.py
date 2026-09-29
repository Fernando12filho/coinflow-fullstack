import time
import requests
from flask import Blueprint, current_app, jsonify, request, g
from app.auth import login_required
from app.db import get_db

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


def _profit_loss(amount, invested, current_price):
    """Return (current value, profit/loss, profit/loss %) or Nones if price is unknown"""
    if not current_price:
        return None, None, None
    value = amount * current_price
    profit_loss = value - invested
    percent = (profit_loss / invested * 100) if invested > 0 else 0
    return value, profit_loss, percent


@bp.route('/holdings', methods=['GET'])
@login_required
def get_holdings():
    """Get user's Bitcoin holdings"""
    db = get_db()
    holdings = db.execute(
        'SELECT * FROM bitcoin_holding WHERE user_id = ? ORDER BY purchase_date DESC',
        (g.user['id'],)
    ).fetchall()

    current_price = get_bitcoin_price()

    holdings_list = []
    total_amount = 0
    total_invested = 0

    for holding in holdings:
        amount = holding['amount']
        purchase_price = holding['purchase_price']
        invested = amount * purchase_price

        total_amount += amount
        total_invested += invested

        # Without a current price, value and profit/loss are unknown (None)
        holding_current_value, profit_loss, profit_loss_percent = _profit_loss(
            amount, invested, current_price
        )

        holdings_list.append({
            'id': holding['id'],
            'amount': amount,
            'purchase_price': purchase_price,
            'purchase_date': holding['purchase_date'],
            'invested': invested,
            'current_value': holding_current_value,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
            'notes': holding['notes']
        })

    current_value, total_profit_loss, total_profit_loss_percent = _profit_loss(
        total_amount, total_invested, current_price
    )

    return jsonify({
        'success': True,
        'holdings': holdings_list,
        'summary': {
            'total_amount': total_amount,
            'total_invested': total_invested,
            'current_value': current_value,
            'current_price': current_price,
            'total_profit_loss': total_profit_loss,
            'total_profit_loss_percent': total_profit_loss_percent
        }
    })


@bp.route('/holdings', methods=['POST'])
@login_required
def add_holding():
    """Add a new Bitcoin holding"""
    data = request.get_json(silent=True) or {}

    amount = data.get('amount')
    purchase_price = data.get('purchase_price')
    notes = data.get('notes', '')

    if not amount or not purchase_price:
        return jsonify({'success': False, 'error': 'Amount and purchase price are required'}), 400

    try:
        amount = float(amount)
        purchase_price = float(purchase_price)
        
        if amount <= 0 or purchase_price <= 0:
            return jsonify({'success': False, 'error': 'Amount and price must be positive'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Invalid number format'}), 400

    db = get_db()
    holding_id = db.execute(
        'INSERT INTO bitcoin_holding (user_id, amount, purchase_price, notes) VALUES (?, ?, ?, ?) RETURNING id',
        (g.user['id'], amount, purchase_price, notes)
    ).fetchone()['id']
    
    # Record transaction
    db.execute(
        'INSERT INTO transaction_history (user_id, transaction_type, amount, price, total_value) VALUES (?, ?, ?, ?, ?)',
        (g.user['id'], 'BUY', amount, purchase_price, amount * purchase_price)
    )
    
    db.commit()

    return jsonify({'success': True, 'holding_id': holding_id})


@bp.route('/holdings/<int:holding_id>', methods=['DELETE'])
@login_required
def delete_holding(holding_id):
    """Delete a Bitcoin holding"""
    db = get_db()
    
    # Verify ownership
    holding = db.execute(
        'SELECT * FROM bitcoin_holding WHERE id = ? AND user_id = ?',
        (holding_id, g.user['id'])
    ).fetchone()

    if not holding:
        return jsonify({'success': False, 'error': 'Holding not found'}), 404

    # Record transaction
    db.execute(
        'INSERT INTO transaction_history (user_id, transaction_type, amount, price, total_value) VALUES (?, ?, ?, ?, ?)',
        (g.user['id'], 'SELL', holding['amount'], holding['purchase_price'], holding['amount'] * holding['purchase_price'])
    )
    
    db.execute('DELETE FROM bitcoin_holding WHERE id = ?', (holding_id,))
    db.commit()

    return jsonify({'success': True})


@bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get user's transaction history"""
    db = get_db()
    transactions = db.execute(
        'SELECT * FROM transaction_history WHERE user_id = ? ORDER BY transaction_date DESC LIMIT 50',
        (g.user['id'],)
    ).fetchall()

    transactions_list = [{
        'id': t['id'],
        'type': t['transaction_type'],
        'amount': t['amount'],
        'price': t['price'],
        'total_value': t['total_value'],
        'date': t['transaction_date']
    } for t in transactions]

    return jsonify({'success': True, 'transactions': transactions_list})

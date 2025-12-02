import requests
from flask import Blueprint, jsonify, request, g
from app.auth import login_required
from app.db import get_db
from datetime import datetime

bp = Blueprint('bitcoin', __name__, url_prefix='/api/bitcoin')


def get_bitcoin_price():
    """Fetch current Bitcoin price from CoinGecko API"""
    try:
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data['bitcoin']['usd']
    except Exception as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None


@bp.route('/price', methods=['GET'])
def get_price():
    """Get current Bitcoin price"""
    price = get_bitcoin_price()
    if price:
        return jsonify({'success': True, 'price': price})
    return jsonify({'success': False, 'error': 'Unable to fetch price'}), 500


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
    current_value = 0

    for holding in holdings:
        amount = holding['amount']
        purchase_price = holding['purchase_price']
        invested = amount * purchase_price
        
        total_amount += amount
        total_invested += invested
        
        if current_price:
            holding_current_value = amount * current_price
            current_value += holding_current_value
            profit_loss = holding_current_value - invested
            profit_loss_percent = (profit_loss / invested * 100) if invested > 0 else 0
        else:
            holding_current_value = 0
            profit_loss = 0
            profit_loss_percent = 0

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

    total_profit_loss = current_value - total_invested
    total_profit_loss_percent = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0

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
    data = request.get_json()
    
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
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid number format'}), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO bitcoin_holding (user_id, amount, purchase_price, notes) VALUES (?, ?, ?, ?)',
        (g.user['id'], amount, purchase_price, notes)
    )
    
    # Record transaction
    db.execute(
        'INSERT INTO transaction_history (user_id, transaction_type, amount, price, total_value) VALUES (?, ?, ?, ?, ?)',
        (g.user['id'], 'BUY', amount, purchase_price, amount * purchase_price)
    )
    
    db.commit()

    return jsonify({'success': True, 'holding_id': cursor.lastrowid})


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

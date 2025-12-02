from flask import Blueprint, jsonify, request, g
from app.db import get_db
from app.auth import login_required

bp = Blueprint('newsletter', __name__, url_prefix='/api/newsletter')


@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe to newsletter"""
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    # Basic email validation
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'error': 'Invalid email format'}), 400

    db = get_db()
    user_id = g.user['id'] if g.user else None

    try:
        # Check if already subscribed
        existing = db.execute(
            'SELECT * FROM newsletter_subscription WHERE email = ?',
            (email,)
        ).fetchone()

        if existing:
            if existing['is_active']:
                return jsonify({'success': False, 'error': 'Email already subscribed'}), 400
            else:
                # Reactivate subscription
                db.execute(
                    'UPDATE newsletter_subscription SET is_active = 1 WHERE email = ?',
                    (email,)
                )
        else:
            db.execute(
                'INSERT INTO newsletter_subscription (user_id, email) VALUES (?, ?)',
                (user_id, email)
            )
        
        db.commit()
        return jsonify({'success': True, 'message': 'Successfully subscribed to newsletter'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/unsubscribe', methods=['POST'])
def unsubscribe():
    """Unsubscribe from newsletter"""
    data = request.get_json() if request.is_json else request.form
    email = data.get('email')

    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400

    db = get_db()
    
    result = db.execute(
        'UPDATE newsletter_subscription SET is_active = 0 WHERE email = ? AND is_active = 1',
        (email,)
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify({'success': False, 'error': 'Email not found or already unsubscribed'}), 404

    return jsonify({'success': True, 'message': 'Successfully unsubscribed'})


@bp.route('/status', methods=['GET'])
@login_required
def get_status():
    """Get subscription status for logged-in user"""
    db = get_db()
    
    subscription = db.execute(
        'SELECT * FROM newsletter_subscription WHERE user_id = ? AND is_active = 1',
        (g.user['id'],)
    ).fetchone()

    if subscription:
        return jsonify({
            'success': True,
            'subscribed': True,
            'email': subscription['email']
        })
    
    return jsonify({'success': True, 'subscribed': False})

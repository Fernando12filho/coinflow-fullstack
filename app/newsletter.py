from flask import Blueprint, current_app, jsonify, request, g
from app.db import get_db
from app.auth import login_required

bp = Blueprint('newsletter', __name__, url_prefix='/api/newsletter')


@bp.route('/subscribe', methods=['POST'])
def subscribe():
    """Subscribe to newsletter"""
    data = request.get_json(silent=True) if request.is_json else request.form
    email = ((data or {}).get('email') or '').strip().lower()

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
                    'UPDATE newsletter_subscription SET is_active = 1, user_id = COALESCE(user_id, ?) WHERE email = ?',
                    (user_id, email)
                )
        else:
            db.execute(
                'INSERT INTO newsletter_subscription (user_id, email) VALUES (?, ?)',
                (user_id, email)
            )
        
        db.commit()
        return jsonify({'success': True, 'message': 'Successfully subscribed to newsletter'})
    except Exception:
        db.rollback()
        current_app.logger.exception('Newsletter subscription failed')
        return jsonify({'success': False, 'error': 'Subscription failed, please try again'}), 500


@bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    """Unsubscribe the logged-in user from the newsletter"""
    db = get_db()

    result = db.execute(
        'UPDATE newsletter_subscription SET is_active = 0 WHERE user_id = ? AND is_active = 1',
        (g.user['id'],)
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify({'success': False, 'error': 'No active subscription found'}), 404

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

"""Account data actions.

Routes:
    POST /api/account/delete-data   delete all trades, imports and settings (keeps the account)
"""
from flask import Blueprint, g, jsonify, request

from app.auth import login_required
from app.db import get_db

bp = Blueprint('account', __name__, url_prefix='/api/account')

CONFIRM_WORD = 'DELETE'


@bp.route('/delete-data', methods=['POST'])
@login_required
def delete_data():
    data = request.get_json(silent=True) or {}
    if data.get('confirm') != CONFIRM_WORD:
        return jsonify({'success': False, 'error': f'Type {CONFIRM_WORD} to confirm'}), 400

    db = get_db()
    user_id = g.user['id']
    trades = db.execute('DELETE FROM trades WHERE user_id = ?', (user_id,)).rowcount
    imports = db.execute('DELETE FROM imports WHERE user_id = ?', (user_id,)).rowcount
    db.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
    db.commit()
    return jsonify({'success': True, 'deleted': {'trades': trades, 'imports': imports}})

"""Per-user display settings: currency, Bitcoin unit and number format.

Routes:
    GET /api/settings   current settings plus the allowed options
    PUT /api/settings   change one or more settings

Settings only change how amounts are shown. Trades are always stored exactly as
entered, in their own currency.
"""
from flask import Blueprint, g, jsonify, request

from app.auth import login_required
from app.db import get_db

bp = Blueprint('settings', __name__, url_prefix='/api/settings')

CURRENCIES = [
    ('USD', 'US dollar ($)'),
    ('EUR', 'Euro (€)'),
    ('GBP', 'British pound (£)'),
    ('BRL', 'Brazilian real (R$)'),
]
BTC_UNITS = ['BTC', 'sats']
LOCALES = [
    ('auto', 'Automatic (from your browser)'),
    ('en-US', 'English (US)'),
    ('en-GB', 'English (UK)'),
    ('pt-BR', 'Português (Brasil)'),
    ('de-DE', 'Deutsch'),
    ('es-ES', 'Español'),
    ('fr-FR', 'Français'),
]
DEFAULTS = {'currency': 'USD', 'btc_unit': 'BTC', 'locale': 'auto'}
CHOICES = {
    'currency': ('Currency', [code for code, _ in CURRENCIES]),
    'btc_unit': ('Bitcoin unit', BTC_UNITS),
    'locale': ('Number format', [code for code, _ in LOCALES]),
}


def get_settings(user_id):
    row = get_db().execute(
        'SELECT currency, btc_unit, locale FROM user_settings WHERE user_id = ?', (user_id,)
    ).fetchone()
    return {key: row[key] for key in DEFAULTS} if row else dict(DEFAULTS)


def options():
    return {
        'currencies': [code for code, _ in CURRENCIES],
        'currency_labels': dict(CURRENCIES),
        'btc_units': BTC_UNITS,
        'locales': [{'code': code, 'label': label} for code, label in LOCALES],
    }


@bp.app_context_processor
def inject_settings():
    """Make the logged-in user's settings available to every template"""
    user = g.get('user')
    return {'user_settings': get_settings(user['id']) if user else None}


@bp.route('', methods=['GET'])
@login_required
def read_settings():
    return jsonify({'success': True, 'settings': get_settings(g.user['id']), 'options': options()})


@bp.route('', methods=['PUT'])
@login_required
def update_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'success': False, 'error': 'Request body must be a JSON object'}), 400

    settings = get_settings(g.user['id'])
    for key, value in data.items():
        if key not in CHOICES:
            return jsonify({'success': False, 'error': f'Unknown setting: {key}'}), 400
        label, allowed = CHOICES[key]
        if value not in allowed:
            return jsonify({'success': False, 'error': f'{label} must be one of: {", ".join(allowed)}'}), 400
        settings[key] = value

    db = get_db()
    db.execute(
        'INSERT INTO user_settings (user_id, currency, btc_unit, locale) VALUES (?, ?, ?, ?) '
        'ON CONFLICT (user_id) DO UPDATE SET currency = excluded.currency, '
        'btc_unit = excluded.btc_unit, locale = excluded.locale',
        (g.user['id'], settings['currency'], settings['btc_unit'], settings['locale']),
    )
    db.commit()
    return jsonify({'success': True, 'settings': settings})

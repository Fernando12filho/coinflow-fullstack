import time
import requests
from flask import Blueprint, current_app, jsonify

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

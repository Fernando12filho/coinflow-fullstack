"""Tell desktop users when a newer CoinFlow release exists.

Routes:
    GET /api/updates   {current, update: {version, url} | None}

Only the desktop app asks GitHub (the website is updated by deploying). The request
carries nothing but a generic "CoinFlow/<version>" User-Agent, happens at most every
few hours, and failures are silent: no answer just means no update is shown.
"""
import re
import time

import requests
from flask import Blueprint, current_app, jsonify

from app.auth import login_required
from app.version import __version__

bp = Blueprint('updates', __name__, url_prefix='/api/updates')

RELEASES_URL = 'https://api.github.com/repos/Fernando12filho/coinflow-fullstack/releases/latest'
RELEASE_PAGE_PREFIX = 'https://github.com/'
CHECK_INTERVAL_SECONDS = 6 * 3600
TIMEOUT = 5

_cache = {'checked_at': None, 'release': None}  # checked_at None = never checked


def reset_cache():
    _cache.update(checked_at=None, release=None)


def parse_version(text):
    """'v1.2.3' or '1.2.3' -> (1, 2, 3); anything else -> None"""
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', (text or '').strip())
    return tuple(int(part) for part in match.groups()) if match else None


def latest_release():
    """{'version', 'url'} of the latest published release, or None (cached)"""
    now = time.time()
    if _cache['checked_at'] is not None and now - _cache['checked_at'] < CHECK_INTERVAL_SECONDS:
        return _cache['release']
    _cache['checked_at'] = now
    try:
        response = requests.get(RELEASES_URL, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': f'CoinFlow/{__version__}',
        }, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except Exception:  # offline, rate limited, no releases yet...
        _cache['release'] = None
        return None

    version = parse_version(data.get('tag_name'))
    url = data.get('html_url') or ''
    valid = version and url.startswith(RELEASE_PAGE_PREFIX) and not data.get('draft') and not data.get('prerelease')
    _cache['release'] = {'version': '.'.join(map(str, version)), 'url': url} if valid else None
    return _cache['release']


def check(current=__version__):
    """The latest release if it is newer than `current`, else None"""
    release = latest_release()
    if release and parse_version(release['version']) > parse_version(current):
        return release
    return None


@bp.route('', methods=['GET'])
@login_required
def get_updates():
    update = check() if current_app.config.get('DESKTOP') else None
    return jsonify({'success': True, 'current': __version__, 'update': update})

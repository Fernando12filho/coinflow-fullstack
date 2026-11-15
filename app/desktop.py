"""Configuration for the installable desktop app.

The desktop app is the same Flask app (same pages, same login), running on the
user's own computer:

- the SQLite database and a secret key live in the user's app-data folder
  (macOS: ~/Library/Application Support/CoinFlow, Windows: %APPDATA%\\CoinFlow,
  Linux: $XDG_DATA_HOME/coinflow or ~/.local/share/coinflow);
- the hosted Postgres database (DATABASE_URL) is never used;
- the local server only answers requests addressed to 127.0.0.1 or localhost, and
  ignores X-Forwarded-* headers, so a web page can't reach it by DNS rebinding.
"""
import os
import secrets
import sys
from pathlib import Path

from app import create_app

APP_NAME = 'CoinFlow'
LOCAL_HOSTS = ['127.0.0.1', 'localhost']


def data_dir(platform=None, env=None, home=None):
    """The folder where the desktop app keeps its data"""
    platform = platform or sys.platform
    env = os.environ if env is None else env
    home = home or Path.home()
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / APP_NAME
    if platform.startswith('win'):
        return Path(env.get('APPDATA') or home / 'AppData' / 'Roaming') / APP_NAME
    return Path(env.get('XDG_DATA_HOME') or home / '.local' / 'share') / APP_NAME.lower()


def load_secret_key(folder):
    """The app's secret key, created on first launch and readable only by the user"""
    path = Path(folder) / 'secret_key'
    if path.exists():
        return path.read_text().strip()
    key = secrets.token_hex(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(key)
    return key


def desktop_config(folder):
    folder = Path(folder)
    return {
        'DESKTOP': True,
        'DATABASE': str(folder / 'coinflow.sqlite'),
        'DATABASE_URL': None,
        'SECRET_KEY': load_secret_key(folder),
        'SESSION_COOKIE_SECURE': False,   # plain http on 127.0.0.1
        'TRUSTED_HOSTS': LOCAL_HOSTS,
    }


def create_desktop_app(folder=None):
    folder = Path(folder) if folder else data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return create_app(desktop_config(folder))

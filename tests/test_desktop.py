"""Tests for the desktop configuration (PLAN.md Phase 8.1)."""
import os
import stat
from pathlib import Path

import pytest

from app import desktop
from app.db import get_db


# ---------- Where data lives ----------

def test_data_dir_on_macos():
    assert desktop.data_dir('darwin', {}, Path('/Users/ana')) == \
        Path('/Users/ana/Library/Application Support/CoinFlow')


def test_data_dir_on_windows():
    assert desktop.data_dir('win32', {'APPDATA': r'C:\Users\ana\AppData\Roaming'}, Path('C:/Users/ana')) == \
        Path(r'C:\Users\ana\AppData\Roaming') / 'CoinFlow'
    assert desktop.data_dir('win32', {}, Path('/home/ana')) == Path('/home/ana/AppData/Roaming/CoinFlow')


def test_data_dir_on_linux():
    assert desktop.data_dir('linux', {}, Path('/home/ana')) == Path('/home/ana/.local/share/coinflow')
    assert desktop.data_dir('linux', {'XDG_DATA_HOME': '/data'}, Path('/home/ana')) == Path('/data/coinflow')


# ---------- Secret key ----------

def test_secret_key_is_created_once_and_private(tmp_path):
    key = desktop.load_secret_key(tmp_path)
    assert len(key) == 64 and int(key, 16)
    assert desktop.load_secret_key(tmp_path) == key            # same key on the next launch
    mode = stat.S_IMODE(os.stat(tmp_path / 'secret_key').st_mode)
    if os.name == 'posix':
        assert mode == 0o600                                    # only the user can read it


# ---------- The desktop app ----------

@pytest.fixture
def desktop_app(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://should-not-be-used/db')
    return desktop.create_desktop_app(tmp_path / 'CoinFlow')


def test_desktop_app_keeps_everything_in_the_data_folder(desktop_app, tmp_path):
    folder = tmp_path / 'CoinFlow'
    assert desktop_app.config['DATABASE'] == str(folder / 'coinflow.sqlite')
    assert desktop_app.config['DATABASE_URL'] is None           # never the hosted database
    assert desktop_app.config['SECRET_KEY'] == (folder / 'secret_key').read_text()
    assert desktop_app.config['DESKTOP'] is True
    with desktop_app.app_context():
        assert get_db().execute('SELECT COUNT(*) AS n FROM trades').fetchone()['n'] == 0
    assert (folder / 'coinflow.sqlite').exists()


def test_desktop_app_has_the_same_pages(desktop_app):
    client = desktop_app.test_client()
    assert client.get('/', base_url='http://127.0.0.1:5123').headers['Location'] == '/auth/login'
    assert client.get('/auth/register', base_url='http://127.0.0.1:5123').status_code == 200


@pytest.mark.parametrize('base_url', ['http://127.0.0.1:5123', 'http://localhost:5123'])
def test_desktop_app_answers_local_addresses(desktop_app, base_url):
    assert desktop_app.test_client().get('/healthz', base_url=base_url).status_code == 200


def test_desktop_app_refuses_other_host_names(desktop_app):
    # A web page using DNS rebinding reaches 127.0.0.1 but its requests carry its own host name
    response = desktop_app.test_client().get('/healthz', base_url='http://evil.example:5123')
    assert response.status_code == 400


def test_desktop_app_ignores_proxy_headers(desktop_app):
    response = desktop_app.test_client().get('/healthz', base_url='http://evil.example:5123',
                                             headers={'X-Forwarded-Host': '127.0.0.1'})
    assert response.status_code == 400


def test_website_still_trusts_its_proxy(app):
    # On Render the app sits behind a proxy and must keep honouring X-Forwarded-* headers
    response = app.test_client().get('/healthz', headers={'X-Forwarded-Host': 'coinflow.example'})
    assert response.status_code == 200


def test_desktop_app_writes_nothing_next_to_its_code(tmp_path, monkeypatch):
    # Inside a packaged app the code folder is read-only (and writing there breaks the macOS signature)
    made = []
    real_makedirs = os.makedirs
    monkeypatch.setattr(os, 'makedirs', lambda path, *a, **k: (made.append(str(path)), real_makedirs(path, *a, **k)))
    app = desktop.create_desktop_app(tmp_path / 'data')
    assert app.instance_path not in made


# ---------- Packaging (PLAN.md Phase 8.3) ----------

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_defined():
    from app.version import __version__
    major, minor, patch = (int(part) for part in __version__.split('.'))
    assert (major, minor, patch) >= (1, 0, 0)


def test_build_spec_bundles_everything_the_app_reads():
    spec = (ROOT / 'coinflow.spec').read_text()
    for path in ('app/templates', 'app/static', 'app/schema.sql', 'coinflow_desktop.py',
                 'packaging/entitlements.plist', 'packaging/coinflow.png'):
        assert path in spec, path
        assert (ROOT / path).exists(), path


def test_icon_is_a_square_png():
    data = (ROOT / 'packaging' / 'coinflow.png').read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    width, height = int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    assert width == height >= 512


def test_entitlements_allow_python_to_run_under_the_hardened_runtime():
    plist = (ROOT / 'packaging' / 'entitlements.plist').read_text()
    for key in ('com.apple.security.cs.allow-unsigned-executable-memory',
                'com.apple.security.cs.disable-library-validation'):
        assert key in plist

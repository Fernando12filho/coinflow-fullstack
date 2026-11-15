"""Tests for the desktop launcher (PLAN.md Phase 8.2). No window is opened: `webview` is faked."""
import sys
import types
import urllib.request

import pytest

from app import launcher


def test_start_server_listens_on_localhost_only(tmp_path):
    app = launcher.create_desktop_app(tmp_path)
    server, url = launcher.start_server(app)
    try:
        assert url.startswith('http://127.0.0.1:')
        assert server.server_address[0] == '127.0.0.1'
        with urllib.request.urlopen(f'{url}/healthz', timeout=5) as response:
            assert response.status == 200
    finally:
        server.shutdown()


def test_smoke_test_mode(tmp_path, capsys):
    assert launcher.main(['--smoke-test', '--data-dir', str(tmp_path)]) == 0
    assert 'CoinFlow desktop smoke test passed' in capsys.readouterr().out
    assert (tmp_path / 'coinflow.sqlite').exists()


def test_smoke_test_reports_failure(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(launcher, 'PAGES_TO_CHECK', ['/healthz', '/no-such-page'])
    assert launcher.main(['--smoke-test', '--data-dir', str(tmp_path)]) == 1
    assert 'failed' in capsys.readouterr().out


@pytest.fixture
def fake_webview(monkeypatch):
    calls = {}
    module = types.SimpleNamespace(settings={})
    module.create_window = lambda title, url, **kwargs: calls.update(window=(title, url, kwargs))
    module.start = lambda **kwargs: calls.update(start=kwargs)
    monkeypatch.setitem(sys.modules, 'webview', module)
    return module, calls


def test_opens_a_native_window(tmp_path, fake_webview):
    module, calls = fake_webview
    assert launcher.main(['--data-dir', str(tmp_path)]) == 0
    title, url, options = calls['window']
    assert title == 'CoinFlow'
    assert url.startswith('http://127.0.0.1:')
    assert options['width'] >= 1200 and options['min_size'] == (400, 600)
    assert calls['start']['private_mode'] is True        # nothing kept in the window's own storage
    assert module.settings['ALLOW_DOWNLOADS'] is True     # CSV export
    assert module.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] is True

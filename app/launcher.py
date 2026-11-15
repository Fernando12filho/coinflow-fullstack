"""Start the CoinFlow desktop app: a local server plus a native window.

    python coinflow_desktop.py                 open the app
    python coinflow_desktop.py --smoke-test    start, check that pages load, exit (for builds and CI)
    python coinflow_desktop.py --data-dir DIR  keep data somewhere other than the app-data folder

The server listens on 127.0.0.1 only, on a random free port, and stops when the
window closes.
"""
import argparse
import logging
import threading
import urllib.request

from werkzeug.serving import make_server

from app.desktop import APP_NAME, create_desktop_app

PAGES_TO_CHECK = ['/healthz', '/auth/login']


def start_server(app):
    """Serve the app on 127.0.0.1 in a background thread. Returns (server, url)."""
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_port}'


def smoke_test(url):
    """True if every page in PAGES_TO_CHECK answers 200"""
    for path in PAGES_TO_CHECK:
        try:
            with urllib.request.urlopen(f'{url}{path}', timeout=10) as response:
                if response.status != 200:
                    return False
        except Exception:
            return False
    return True


def open_window(url):
    import webview  # imported here so the website and tests don't need it

    webview.settings['ALLOW_DOWNLOADS'] = True                 # CSV export
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True  # e.g. tradingview.com, release page
    webview.create_window(APP_NAME, url, width=1280, height=860, min_size=(400, 600))
    webview.start(private_mode=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog='coinflow', description='CoinFlow desktop app')
    parser.add_argument('--smoke-test', action='store_true', help='start, check pages load, then exit')
    parser.add_argument('--data-dir', help='folder for the database and secret key')
    args = parser.parse_args(argv)

    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    app = create_desktop_app(args.data_dir)
    server, url = start_server(app)
    try:
        if args.smoke_test:
            ok = smoke_test(url)
            print(f'CoinFlow desktop smoke test {"passed" if ok else "failed"} ({url})')
            return 0 if ok else 1
        open_window(url)
        return 0
    finally:
        server.shutdown()

"""Tests for the desktop update check (PLAN.md Phase 8.5). GitHub is faked."""
import pytest

from app import desktop, updates
from app.version import __version__


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status = payload, status

    def raise_for_status(self):
        if self.status >= 400:
            raise updates.requests.HTTPError(str(self.status))

    def json(self):
        return self.payload


@pytest.fixture
def github(monkeypatch):
    state = {'tag': 'v9.0.0', 'url': 'https://github.com/Fernando12filho/coinflow-fullstack/releases/tag/v9.0.0',
             'fail': False, 'calls': []}

    def get(url, headers, timeout):
        state['calls'].append((url, headers))
        if state['fail']:
            raise updates.requests.ConnectionError('offline')
        return FakeResponse({'tag_name': state['tag'], 'html_url': state['url'], 'draft': False, 'prerelease': False})

    monkeypatch.setattr(updates.requests, 'get', get)
    updates.reset_cache()
    return state


@pytest.mark.parametrize('text, expected', [
    ('v1.2.3', (1, 2, 3)), ('1.10.0', (1, 10, 0)), ('v1.2', None), ('latest', None), ('', None),
])
def test_parse_version(text, expected):
    assert updates.parse_version(text) == expected


def test_newer_release_is_offered(github):
    assert updates.check('1.0.0') == {'version': '9.0.0', 'url': github['url']}
    url, headers = github['calls'][0]
    assert url == updates.RELEASES_URL
    assert headers['User-Agent'] == f'CoinFlow/{__version__}'   # a generic app name, nothing personal


@pytest.mark.parametrize('tag', ['v1.0.0', 'v0.9.9', 'nightly'])
def test_same_older_or_odd_releases_are_not_offered(github, tag):
    github['tag'] = tag
    assert updates.check('1.0.0') is None


def test_only_github_release_pages_are_linked(github):
    github['url'] = 'https://evil.example/download'
    assert updates.check('1.0.0') is None


def test_offline_means_no_update(github):
    github['fail'] = True
    assert updates.check('1.0.0') is None


def test_github_is_asked_at_most_every_few_hours(github, monkeypatch):
    clock = {'now': 1000.0}
    monkeypatch.setattr(updates.time, 'time', lambda: clock['now'])
    updates.check('1.0.0')
    updates.check('1.0.0')
    assert len(github['calls']) == 1
    clock['now'] += updates.CHECK_INTERVAL_SECONDS + 1
    updates.check('1.0.0')
    assert len(github['calls']) == 2


# ---------- API and page ----------

def sign_up(client, base_url):
    client.post('/auth/register', base_url=base_url,
                data={'username': 'ana', 'email': 'ana@example.com', 'password': 'secret12'})
    client.post('/auth/login', base_url=base_url, data={'username': 'ana', 'password': 'secret12'})


def test_website_never_checks_for_updates(logged_in, github):
    body = logged_in.get('/api/updates').get_json()
    assert body == {'success': True, 'current': __version__, 'update': None}
    assert github['calls'] == []
    assert 'id="update-link"' not in logged_in.get('/').data.decode()


def test_desktop_app_reports_an_update(tmp_path, github):
    app = desktop.create_desktop_app(tmp_path)
    client = app.test_client()
    base = 'http://127.0.0.1:5123'
    sign_up(client, base)
    body = client.get('/api/updates', base_url=base).get_json()
    assert body['update'] == {'version': '9.0.0', 'url': github['url']}
    html = client.get('/settings', base_url=base).data.decode()
    assert 'id="update-link"' in html


def test_updates_require_login(client):
    assert client.get('/api/updates').status_code == 401

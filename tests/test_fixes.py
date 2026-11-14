"""Tests for the fixes in PLAN.md Phase 1."""
import pytest
from conftest import register, login


def add(client, **extra):
    return client.post('/api/bitcoin/holdings', json={'amount': 0.1, 'purchase_price': 30000, **extra})


# F2: notes are reachable and validated

def test_dashboard_form_has_notes_field(logged_in):
    page = logged_in.get('/').data
    assert b'name="notes"' in page
    assert b'<th>Notes</th>' in page


def test_notes_are_trimmed(logged_in):
    add(logged_in, notes='  bought on the dip  ')
    assert logged_in.get('/api/bitcoin/holdings').get_json()['holdings'][0]['notes'] == 'bought on the dip'


def test_notes_are_optional(logged_in):
    assert add(logged_in).get_json()['success'] is True
    assert add(logged_in, notes=None).get_json()['success'] is True


@pytest.mark.parametrize('notes', [123, ['a'], 'x' * 501])
def test_invalid_notes_are_rejected(logged_in, notes):
    response = add(logged_in, notes=notes)
    assert response.status_code == 400
    assert 'Notes' in response.get_json()['error']


# F3: login does not reveal which usernames exist; passwords need 8+ characters

def test_unknown_username_and_wrong_password_look_the_same(client):
    register(client)
    unknown = login(client, username='nobody').data
    wrong = login(client, password='wrong-pass').data
    assert b'Invalid username or password.' in unknown
    assert b'Invalid username or password.' in wrong
    assert b'Incorrect username' not in unknown


def test_login_without_password_is_rejected(client):
    register(client)
    response = client.post('/auth/login', data={'username': 'alice'})
    assert b'Invalid username or password.' in response.data


@pytest.mark.parametrize('password', ['abc12', 'seven77'])
def test_register_rejects_passwords_under_8_characters(client, password):
    response = register(client, password=password)
    assert b'Password must be at least 8 characters.' in response.data
    assert b'Invalid username or password.' in login(client, password=password).data


def test_register_accepts_8_character_password(client):
    register(client, password='eight888')
    assert login(client, password='eight888').headers['Location'] == '/'


def test_register_form_matches_password_rule(client):
    page = client.get('/auth/register').data
    assert b'minlength="8"' in page
    assert b'At least 8 characters' in page

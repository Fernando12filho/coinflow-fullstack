"""Importing exchange CSV files into the trade ledger.

Routes:
    POST   /api/imports/preview   read a file and report what an import would do (saves nothing)
    POST   /api/imports           import a file's new trades
    GET    /api/imports           files imported so far
    DELETE /api/imports/<id>      remove an import and its trades

Duplicates are caught twice: the exact same file (by SHA-256) is refused, and
trades already stored (by each trade's stable id) are skipped. The whole ledger
is replayed before saving, so an import can never leave an impossible history.
"""
import hashlib
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from app.auth import login_required
from app.db import get_db
from app.importers import ImportFormatError, parse_file
from app.ledger import BUY, REWARD, SELL, LedgerError
from app.portfolio import check_history, fmt, insert_trade, load_rows, row_to_trade

bp = Blueprint('imports', __name__, url_prefix='/api/imports')

MAX_SKIPPED_SHOWN = 200
MAX_FILENAME_LENGTH = 200


def _error(message, status=400):
    return jsonify({'success': False, 'error': message}), status


def _date(value):
    if value is None:
        return None
    value = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    return value.strftime('%Y-%m-%d')


def _read_upload():
    """(filename, bytes) of the uploaded file, or raise ValueError"""
    upload = request.files.get('file')
    if upload is None or not upload.filename:
        raise ValueError('Choose a CSV file to import')
    return upload.filename[:MAX_FILENAME_LENGTH], upload.read()


def _analyse(content):
    """Parse a file and work out what importing it would do for the current user"""
    parsed = parse_file(content)
    db = get_db()
    user_id = g.user['id']
    file_hash = hashlib.sha256(content).hexdigest()

    previous = db.execute(
        'SELECT imported_at FROM imports WHERE user_id = ? AND file_hash = ?', (user_id, file_hash)
    ).fetchone()
    stored = {row['trade_hash'] for row in db.execute(
        'SELECT trade_hash FROM trades WHERE user_id = ? AND trade_hash IS NOT NULL', (user_id,)
    ).fetchall()}

    new, seen = [], set(stored)
    for item in parsed.trades:
        if item.trade_hash not in seen:
            new.append(item)
            seen.add(item.trade_hash)

    problem = None
    if new:
        try:
            check_history([row_to_trade(row) for row in load_rows(user_id)] + [i.trade for i in new])
        except LedgerError as e:
            problem = str(e)

    return {
        'parsed': parsed,
        'file_hash': file_hash,
        'previous': previous,
        'new': new,
        'problem': problem,
    }


def _preview_payload(filename, analysis):
    parsed, new = analysis['parsed'], analysis['new']
    trades = [t.trade for t in parsed.trades]
    count = lambda side: sum(1 for t in new if t.trade.side == side)  # noqa: E731
    return {
        'provider': parsed.provider,
        'filename': filename,
        'trades': len(parsed.trades),
        'new': len(new),
        'duplicates': len(parsed.trades) - len(new),
        'buys': count(BUY),
        'sells': count(SELL),
        'rewards': count(REWARD),
        'date_from': _date(min((t.date for t in trades), default=None)),
        'date_to': _date(max((t.date for t in trades), default=None)),
        'btc_in': fmt(sum((t.trade.btc for t in new if t.trade.side != SELL), start=0) or None),
        'btc_out': fmt(sum((t.trade.btc for t in new if t.trade.side == SELL), start=0) or None),
        'skipped_count': len(parsed.skipped),
        'skipped': [{'line': s.line, 'reason': s.reason} for s in parsed.skipped[:MAX_SKIPPED_SHOWN]],
        'already_imported': analysis['previous'] is not None,
        'problem': analysis['problem'],
    }


def _import_record(row):
    return {
        'id': row['id'],
        'provider': row['provider'],
        'filename': row['filename'],
        'trade_count': row['trade_count'],
        'date_from': _date(row['date_from']),
        'date_to': _date(row['date_to']),
        'imported_at': _date(row['imported_at']),
    }


@bp.route('/preview', methods=['POST'])
@login_required
def preview_import():
    try:
        filename, content = _read_upload()
        analysis = _analyse(content)
    except (ValueError, ImportFormatError) as e:
        return _error(str(e))
    return jsonify({'success': True, 'preview': _preview_payload(filename, analysis)})


@bp.route('', methods=['POST'])
@login_required
def confirm_import():
    try:
        filename, content = _read_upload()
        analysis = _analyse(content)
    except (ValueError, ImportFormatError) as e:
        return _error(str(e))

    parsed, new = analysis['parsed'], analysis['new']
    if analysis['previous'] is not None:
        return _error(f"This file was already imported on {_date(analysis['previous']['imported_at'])}", 409)
    if not new:
        return _error('Every trade in this file is already in CoinFlow' if parsed.trades
                      else 'This file has no BTC trades to import')
    if analysis['problem']:
        return _error(analysis['problem'])

    db = get_db()
    dates = [t.trade.date for t in parsed.trades]
    try:
        import_id = db.execute(
            'INSERT INTO imports (user_id, provider, filename, file_hash, trade_count, date_from, date_to) '
            'VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id',
            (g.user['id'], parsed.provider, filename, analysis['file_hash'], len(new),
             min(dates).isoformat(' '), max(dates).isoformat(' ')),
        ).fetchone()['id']
        for item in new:
            insert_trade(db, g.user['id'], item.trade, item.notes, source=parsed.provider,
                         import_id=import_id, trade_hash=item.trade_hash)
        db.commit()
    except db.IntegrityError:  # the same file or trades were saved by another request meanwhile
        db.rollback()
        return _error('This file was imported at the same time in another window', 409)

    record = db.execute('SELECT * FROM imports WHERE id = ?', (import_id,)).fetchone()
    return jsonify({
        'success': True,
        'import': _import_record(record),
        'added': len(new),
        'duplicates': len(parsed.trades) - len(new),
        'skipped': len(parsed.skipped),
    }), 201


@bp.route('', methods=['GET'])
@login_required
def list_imports():
    rows = get_db().execute(
        'SELECT * FROM imports WHERE user_id = ? ORDER BY imported_at DESC, id DESC', (g.user['id'],)
    ).fetchall()
    return jsonify({'success': True, 'imports': [_import_record(row) for row in rows]})


@bp.route('/<int:import_id>', methods=['DELETE'])
@login_required
def remove_import(import_id):
    db = get_db()
    user_id = g.user['id']
    record = db.execute('SELECT * FROM imports WHERE id = ? AND user_id = ?', (import_id, user_id)).fetchone()
    if record is None:
        return _error('Import not found', 404)

    remaining = [row_to_trade(row) for row in load_rows(user_id) if row['import_id'] != import_id]
    try:
        check_history(remaining)
    except LedgerError as e:
        return _error(f'Removing this import would break your history: {e}')

    db.execute('DELETE FROM trades WHERE import_id = ? AND user_id = ?', (import_id, user_id))
    db.execute('DELETE FROM imports WHERE id = ? AND user_id = ?', (import_id, user_id))
    db.commit()
    return jsonify({'success': True})

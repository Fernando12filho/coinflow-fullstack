import sqlite3
from datetime import datetime
import click
from flask import current_app, g

# Python 3.12 deprecated sqlite3's built-in timestamp converter
sqlite3.register_converter('timestamp', lambda value: datetime.fromisoformat(value.decode()))


def _database_url():
    """Return the Postgres URL if one is configured, otherwise None (use SQLite)"""
    url = current_app.config.get('DATABASE_URL')
    if not url:
        return None
    # Some providers still hand out the legacy "postgres://" scheme
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]
    return url


class PostgresDB:
    """Thin wrapper so Postgres can be used with the same calls as sqlite3"""

    def __init__(self, url):
        import psycopg2
        import psycopg2.extras
        self.IntegrityError = psycopg2.IntegrityError
        self.conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

    def execute(self, sql, params=()):
        cursor = self.conn.cursor()
        cursor.execute(sql.replace('?', '%s'), params)
        return cursor

    def executescript(self, script):
        self.conn.cursor().execute(script)
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_db():
    """Get database connection"""
    if 'db' not in g:
        url = _database_url()
        if url:
            g.db = PostgresDB(url)
        else:
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)

    if db is not None:
        db.close()


def _schema_file():
    return 'schema_postgres.sql' if _database_url() else 'schema.sql'


def create_tables():
    """Create any missing tables without touching existing data"""
    db = get_db()

    with current_app.open_resource(_schema_file()) as f:
        db.executescript(f.read().decode('utf8'))


def init_db():
    """Drop all tables and recreate them (destroys all data)"""
    db = get_db()
    db.executescript(
        'DROP TABLE IF EXISTS transaction_history;'
        'DROP TABLE IF EXISTS newsletter_subscription;'
        'DROP TABLE IF EXISTS bitcoin_holding;'
        'DROP TABLE IF EXISTS users;'
    )
    create_tables()


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    """Register database functions with the Flask app"""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    with app.app_context():
        create_tables()

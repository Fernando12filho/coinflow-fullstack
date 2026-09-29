import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    is_production = os.environ.get('FLASK_ENV') == 'production'

    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        DATABASE=os.path.join(app.instance_path, 'coinflow.sqlite'),
        DATABASE_URL=os.environ.get('DATABASE_URL'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=is_production,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    if is_production and not os.environ.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY must be set when FLASK_ENV=production')

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Trust the X-Forwarded-* headers set by the hosting platform's proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Initialize database
    from . import db
    db.init_app(app)

    # Register blueprints
    from . import auth
    app.register_blueprint(auth.bp)

    from . import bitcoin
    app.register_blueprint(bitcoin.bp)

    from . import newsletter
    app.register_blueprint(newsletter.bp)

    from . import dashboard
    app.register_blueprint(dashboard.bp)

    @app.route('/healthz')
    def healthz():
        return {'status': 'ok'}

    return app

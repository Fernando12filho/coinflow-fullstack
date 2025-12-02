import os
from flask import Flask
from flask_cors import CORS


def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        DATABASE=os.path.join(app.instance_path, 'coinflow.sqlite'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Enable CORS
    CORS(app)

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

    # Home route
    @app.route('/')
    def index():
        return dashboard.index()

    return app

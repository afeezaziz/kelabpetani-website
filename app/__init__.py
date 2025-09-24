from flask import Flask
from flask_wtf import CSRFProtect
from app.extensions import db, limiter, mail
import os
from dotenv import load_dotenv
from flask_wtf.csrf import generate_csrf
from flask import render_template

def create_app():
    # Load .env variables
    load_dotenv()

    app = Flask(__name__, template_folder='templates')

    # Database configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kelab_petani.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.setdefault('WTF_CSRF_ENABLED', True)
    # Session cookie hardening
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    # Toggle secure cookie via env for local dev flexibility
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    # Email configuration (optional)
    app.config['ENABLE_EMAIL'] = os.getenv('ENABLE_EMAIL', 'false').lower() == 'true'
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', '')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'Kelab Petani <no-reply@kelabpetani.local>')

    # Initialize database
    db.init_app(app)

    # CSRF Protection
    CSRFProtect(app)
    # Expose csrf_token() to templates
    app.jinja_env.globals['csrf_token'] = generate_csrf

    # Rate Limiting
    limiter.init_app(app)
    # Mail
    mail.init_app(app)

    # Initialize OAuth
    from app.oauth import init_oauth
    init_oauth(app)

    # Import and register routes
    from app.blueprint import main
    # Ensure route modules are imported so they register handlers on the blueprint
    from app import routes_core, routes_marketplace, routes_orders, routes_pawah, routes_admin  # noqa: F401
    app.register_blueprint(main)

    # Error handlers
    @app.errorhandler(403)
    def forbidden(_e):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template('404.html'), 404

    @app.errorhandler(429)
    def ratelimit(_e):
        return render_template('429.html'), 429

    @app.errorhandler(500)
    def server_error(_e):
        return render_template('500.html'), 500

    return app
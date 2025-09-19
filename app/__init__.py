from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.oauth import init_oauth
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates')

    # Database configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///kelab_petani.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    # Initialize OAuth
    init_oauth(app)

    # Import routes
    from app.routes import main
    app.register_blueprint(main)

    return app
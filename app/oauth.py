from authlib.integrations.flask_client import OAuth
from flask import redirect, url_for, session, flash, jsonify
from app.models import User
from app.extensions import db
from datetime import datetime
import os

oauth = OAuth()

def init_oauth(app):
    oauth.init_app(app)

    # Google OAuth configuration
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    return google

def handle_google_login(google):
    redirect_uri = url_for('main.auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

def handle_google_callback(google):
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token)

        # Check if user exists
        user = User.query.filter_by(email=user_info['email']).first()

        admin_email = os.getenv('ADMIN_EMAIL')
        if not user:
            # Create new user
            user = User(
                google_id=user_info['sub'],
                email=user_info['email'],
                name=user_info['name'],
                profile_picture=user_info.get('picture'),
                is_admin=True if admin_email and admin_email.lower() == user_info['email'].lower() else False
            )
            db.session.add(user)
            db.session.commit()
        else:
            # Update existing user
            user.google_id = user_info['sub']
            user.name = user_info['name']
            user.profile_picture = user_info.get('picture')
            # Promote to admin if email matches ADMIN_EMAIL
            if admin_email and admin_email.lower() == user.email.lower() and not user.is_admin:
                user.is_admin = True
            user.updated_at = datetime.utcnow()
            db.session.commit()

        # Store user in session
        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_name'] = user.name
        session['is_admin'] = user.is_admin

        return redirect(url_for('main.profile'))

    except Exception as e:
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('main.home'))
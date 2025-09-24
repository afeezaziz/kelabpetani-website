from flask import render_template, redirect, url_for, session, flash, current_app
from app.blueprint import main
from app.models import User
from app.oauth import init_oauth, handle_google_login, handle_google_callback, oauth


@main.route('/')
def home():
    return render_template('home.html')


@main.route('/login')
def login():
    def get_google_client():
        client = oauth.create_client('google')
        if not client:
            client = init_oauth(current_app)
        return client

    google = get_google_client()
    return handle_google_login(google)


@main.route('/auth/callback')
def auth_callback():
    def get_google_client():
        client = oauth.create_client('google')
        if not client:
            client = init_oauth(current_app)
        return client

    google = get_google_client()
    return handle_google_callback(google)


@main.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('main.home'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('main.home'))

    return render_template('profile.html', user=user)


@main.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.home'))

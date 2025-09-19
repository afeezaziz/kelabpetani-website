from flask import Blueprint, render_template, redirect, url_for, session, flash
from app import db
from app.oauth import init_oauth, handle_google_login, handle_google_callback

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('home.html')

@main.route('/login')
def login():
    google = init_oauth(main.app)
    return handle_google_login(google)

@main.route('/auth/callback')
def auth_callback():
    google = init_oauth(main.app)
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
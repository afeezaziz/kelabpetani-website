from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import session, request
from flask_mail import Mail

# Central SQLAlchemy instance to avoid circular imports
# Import this as: from app.extensions import db, limiter

db = SQLAlchemy()


def rate_limit_key():
    try:
        uid = session.get('user_id')
        if uid:
            return f"user:{uid}"
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(key_func=rate_limit_key)

# Shared mail instance
mail = Mail()

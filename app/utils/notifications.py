from flask import current_app
from flask_mail import Message
from app.extensions import mail


def safe_send_email(to_email: str, subject: str, body: str) -> bool:
    try:
        app = current_app
        cfg = app.config
        if not cfg.get('ENABLE_EMAIL'):
            return False
        if not cfg.get('MAIL_SERVER') or not to_email:
            return False
        msg = Message(subject=subject, recipients=[to_email])
        msg.body = body
        mail.send(msg)
        return True
    except Exception:
        # Never raise to callers – email is best-effort
        return False

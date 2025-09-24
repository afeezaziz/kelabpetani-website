 # Kelab Petani — Flask App
 
 A simple marketplace and pawah (profit-sharing agriculture) platform built with Flask, SQLAlchemy, and Alembic.
 
 ## Quickstart
 
 - **Python**: 3.11+
 - **Create venv and install deps**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
 - **Configure environment**
   - Copy `.env.example` to `.env` and fill in values (see Environment Variables below)
   ```bash
   cp .env.example .env
   ```
 - **Initialize database**
   ```bash
   alembic upgrade head
   ```
 - **Run the app**
   ```bash
   python app.py
   ```
 
 ## Environment Variables
 
 - `SECRET_KEY`: Flask secret key
 - `DATABASE_URL`: SQLAlchemy URL (default: `sqlite:///kelab_petani.db`)
 - `ADMIN_EMAIL`: Email that should receive admin privileges upon login (Google OAuth)
 - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Google OAuth credentials
 - `SESSION_COOKIE_SECURE`: `true|false` (set `true` in production behind HTTPS)
 - `ENABLE_EMAIL`: `true|false` — enable email notifications via Flask-Mail
 - `MAIL_SERVER`: SMTP server (if `ENABLE_EMAIL=true`)
 - `MAIL_PORT`: SMTP port (e.g., 587)
 - `MAIL_USE_TLS`: `true|false`
 - `MAIL_USE_SSL`: `true|false`
 - `MAIL_USERNAME` / `MAIL_PASSWORD`: SMTP auth
 - `MAIL_DEFAULT_SENDER`: e.g., `Kelab Petani <no-reply@kelabpetani.local>`
 
 See `.env.example` for a working template.
 
 ## Architecture
 
 - **Blueprint**: single blueprint `main` in `app/blueprint.py`
 - **Routes (modularized)**
   - `app/routes_core.py`: Home, OAuth (`/`, `/login`, `/auth/callback`), profile, logout
   - `app/routes_marketplace.py`: Marketplace list, new, detail, my listings, archive/unarchive, edit
   - `app/routes_orders.py`: Orders list/detail, status transitions, messaging
   - `app/routes_pawah.py`: Pawah list/new/detail, accept/start/complete/cancel, messaging
   - `app/routes_admin.py`: Admin dashboard, products, pawah, moderation, audit logs
 - **Models**: `User`, `Product`, `Order`, `PawahProject`, `Message`, `AuditLog` in `app/models.py`
 - **Extensions**: `db`, `limiter`, `mail` in `app/extensions.py`
 - **Templates**: Tailwind + DaisyUI in `app/templates/`
 
 ## Migrations (Alembic)
 
 - Config: `alembic.ini`, env at `alembic/env.py`
 - Create a migration (autogenerate):
   ```bash
   alembic revision -m "your message" --autogenerate
   ```
 - Apply migrations:
   ```bash
   alembic upgrade head
   ```
 
 ## Security & Rate Limiting
 
 - **CSRF**: Flask-WTF enabled app-wide; all POST forms include `csrf_token()`
 - **Rate Limits**: Applied to write endpoints; limiter key prefers `session.user_id` when logged in, falling back to IP
 - **Sanitization**: User messages sanitized with `bleach` (HTML stripped)
 - **Session Cookies**: `HTTPOnly`, `SameSite=Lax` (and `Secure` configurable via env)
 
 ## Admin & Moderation
 
 - Admin granted based on `ADMIN_EMAIL`
 - Product/Pawah moderation captures approval/rejection with reasons and timestamps
 - **Audit Logs** at `/admin/logs` with filters and pagination; links to entities
 
 ## Email Notifications (Optional)
 
 If `ENABLE_EMAIL=true` and SMTP is configured, the app sends notifications for:
 - Order status changes and messages
 - Pawah accept/start/complete/cancel and messages
 - Admin approvals/rejections (with reason)
 
 ## Notes
 
 - URLs remain the same and are namespaced under the `main` blueprint
 - For local development, leave `SESSION_COOKIE_SECURE=false`

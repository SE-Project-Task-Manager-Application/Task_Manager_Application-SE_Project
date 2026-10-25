"""Settings used by the automated tests (pytest sets this in pytest.ini).

Uses the PostgreSQL settings inherited from base.py (DB_NAME, DB_USER, DB_PASSWORD,
DB_HOST, DB_PORT), the same database as production. In CI the workflow provides a
postgres:16 service. Locally, run `docker compose up -d db` and copy `.env.example`
to `.env` first. Only the secret key and the fast password hasher are test-specific.
"""

from .base import *  # noqa: F403

SECRET_KEY = "test-only-not-a-secret"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# E-mail needs no setting here: Django's test runner swaps in an in-memory mail backend
# and collects messages in django.core.mail.outbox.

# Fast hashing keeps the suite quick. Never use this outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

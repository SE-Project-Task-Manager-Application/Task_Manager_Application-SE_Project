"""Settings used by the automated tests (pytest sets this in pytest.ini).

Needs no environment variables, so `pytest` runs on a clean checkout and in CI.
"""

from .base import *  # noqa: F403

SECRET_KEY = "test-only-not-a-secret"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# E-mail needs no setting here: Django's test runner swaps in an in-memory mail backend
# and collects messages in django.core.mail.outbox.

# Fast hashing keeps the suite quick. Never use this outside tests.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

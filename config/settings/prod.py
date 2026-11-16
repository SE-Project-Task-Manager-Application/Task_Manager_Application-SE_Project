import os

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ["DJANGO_ALLOWED_HOSTS"].split(",")
    if host.strip()
]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Require HTTPS in production. The TLS terminator must overwrite
# X-Forwarded-Proto with the actual client connection scheme before forwarding
# requests to Django; never trust this header from arbitrary clients.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

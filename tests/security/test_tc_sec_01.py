"""TC-Sec-01: production traffic must use HTTPS with TLS 1.2 or newer."""

import importlib

from django.test import Client, override_settings


def test_tc_sec_01_production_settings_require_https(monkeypatch):
    """Production settings enforce HTTPS, HSTS, and secure cookies."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-production-secret-key")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.test")

    import config.settings.prod as prod_settings

    prod_settings = importlib.reload(prod_settings)

    assert prod_settings.SECURE_SSL_REDIRECT is True
    assert prod_settings.SECURE_HSTS_SECONDS == 31536000
    assert prod_settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is False
    assert prod_settings.SESSION_COOKIE_SECURE is True
    assert prod_settings.CSRF_COOKIE_SECURE is True
    assert prod_settings.SECURE_PROXY_SSL_HEADER == (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


def test_tc_sec_01_http_redirects_to_https():
    """SecurityMiddleware redirects plaintext requests when enabled."""
    with override_settings(SECURE_SSL_REDIRECT=True):
        response = Client().get("/")

    assert response.status_code == 301
    assert response["Location"].startswith("https://")


def test_tc_sec_01_https_request_is_not_redirected():
    """Requests already using HTTPS proceed normally."""
    with override_settings(SECURE_SSL_REDIRECT=True):
        response = Client().get("/", secure=True)

    assert response.status_code == 200

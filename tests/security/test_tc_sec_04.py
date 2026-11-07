"""TC-Sec-04: Verify Django session expiry after 24 hours of inactivity."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


def test_tc_sec_04_session_lifetime_is_24_hours():
    """Sessions must be configured to expire after 24 hours."""
    assert settings.SESSION_COOKIE_AGE == 60 * 60 * 24
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_tc_sec_04_expired_session_is_rejected(make_user):
    """An expired session must not grant access to protected pages."""
    user = make_user(email="session-expiry@example.com")

    client = Client()
    client.force_login(user)

    session_key = client.cookies[settings.SESSION_COOKIE_NAME].value

    Session.objects.filter(session_key=session_key).update(
        expire_date=timezone.now() - timedelta(seconds=1)
    )

    response = client.get(reverse("tasks:list"))

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))


def test_tc_sec_04_activity_refreshes_session_expiry(make_user):
    """An authenticated request must refresh the session expiry."""
    user = make_user(email="session-activity@example.com")

    client = Client()
    client.force_login(user)

    session_key = client.cookies[settings.SESSION_COOKIE_NAME].value

    Session.objects.filter(session_key=session_key).update(
        expire_date=timezone.now() + timedelta(hours=1)
    )

    response = client.get(reverse("tasks:list"))

    assert response.status_code == 200

    session = Session.objects.get(session_key=session_key)

    assert session.expire_date > timezone.now() + timedelta(hours=23)

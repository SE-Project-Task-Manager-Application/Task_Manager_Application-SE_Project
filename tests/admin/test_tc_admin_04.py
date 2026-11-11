import pytest
from django.core import mail
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.forms import PasswordChangeForm
from django.test import RequestFactory
from django.urls import reverse

from adminpanel.config import get_system_config
from adminpanel.models import AuditRecord, SystemConfig
from adminpanel.middleware import DatabaseSessionTimeoutMiddleware
from notif.services import NotificationEvent, NotificationService


pytestmark = pytest.mark.django_db


def test_admin_can_update_system_config_and_audit_it(client, make_user):
    admin = make_user(role="admin")
    client.force_login(admin)

    response = client.post(
        reverse("adminpanel:update_system_config"),
        {
            "password_min_length": 12,
            "session_timeout_seconds": 1800,
            "notifications_enabled": "",
            "notification_sender": "alerts@example.com",
        },
    )

    assert response.status_code == 302
    config = SystemConfig.objects.get()
    assert config.password_min_length == 12
    assert config.session_timeout_seconds == 1800
    assert not config.notifications_enabled
    assert AuditRecord.objects.filter(action="system_config.updated", actor=admin).exists()


def test_session_timeout_is_capped_at_24_hours(client, make_user):
    admin = make_user(role="admin")
    client.force_login(admin)

    response = client.post(
        reverse("adminpanel:update_system_config"),
        {
            "password_min_length": 8,
            "session_timeout_seconds": 86401,
            "notifications_enabled": "on",
            "notification_sender": "alerts@example.com",
        },
    )

    assert response.status_code == 400
    assert SystemConfig.objects.count() == 1


def test_password_minimum_setting_is_enforced(make_user):
    user = make_user()
    config = get_system_config()
    config.password_min_length = 12
    config.save(update_fields=["password_min_length"])

    short_form = PasswordChangeForm(
        user,
        {"old_password": "SEPROG123", "new_password1": "short", "new_password2": "short"},
    )
    long_form = PasswordChangeForm(
        user,
        {
            "old_password": "SEPROG123",
            "new_password1": "twelve-char1!",
            "new_password2": "twelve-char1!",
        },
    )

    assert not short_form.is_valid()
    assert long_form.is_valid()


def test_session_timeout_setting_is_applied(make_user):
    user = make_user()
    config = get_system_config()
    config.session_timeout_seconds = 1800
    config.save(update_fields=["session_timeout_seconds"])
    request = RequestFactory().get("/")
    request.user = user
    request.session = SessionStore()

    DatabaseSessionTimeoutMiddleware(lambda request: request)(request)

    assert request.session["_session_expiry"] == 1800


def test_notifications_can_be_disabled(make_user):
    config = get_system_config()
    config.notifications_enabled = False
    config.save(update_fields=["notifications_enabled"])
    event = NotificationEvent("test", make_user(), "Subject", "Body")

    assert not NotificationService.send(event)
    assert len(mail.outbox) == 0


def test_member_cannot_update_system_config(client, make_user):
    member = make_user()
    client.force_login(member)

    response = client.get(reverse("adminpanel:system_config"))

    assert response.status_code == 403

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import AuditRecord

pytestmark = pytest.mark.django_db

PASSWORD = "SEPROG123"


def _login(client, email, password):
    return client.post(
        reverse("accounts:login"),
        {"username": email, "password": password},
    )


def test_tc_auth_03_fifth_failure_locks_account_and_logs_audit(client, make_user):
    user = make_user(email="lockout@example.com")

    for _ in range(4):
        response = _login(client, user.email, "wrong-password")
        assert response.status_code == 200

    user.refresh_from_db()
    assert user.failed_login_attempts == 4
    assert user.locked_until is None
    assert not AuditRecord.objects.filter(action="auth.account_locked").exists()

    started_at = timezone.now()
    response = _login(client, user.email, "wrong-password")
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.failed_login_attempts == 5
    assert started_at + timedelta(minutes=14) < user.locked_until
    assert user.locked_until <= started_at + timedelta(minutes=15, seconds=2)

    audit = AuditRecord.objects.get(action="auth.account_locked")
    assert audit.target_type == "user"
    assert audit.target_id == str(user.pk)
    assert audit.details == {"failed_login_attempts": 5}


def test_tc_auth_03_login_during_lock_does_not_extend_it(client, make_user):
    user = make_user(email="locked@example.com")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() + timedelta(minutes=15)
    user.save(update_fields=["failed_login_attempts", "locked_until"])
    original_expiry = user.locked_until

    response = _login(client, user.email, PASSWORD)

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.failed_login_attempts == 5
    assert user.locked_until == original_expiry


def test_tc_auth_03_login_succeeds_after_lock_expiry(client, make_user):
    user = make_user(email="expired-lock@example.com")
    user.failed_login_attempts = 5
    user.locked_until = timezone.now() - timedelta(seconds=1)
    user.save(update_fields=["failed_login_attempts", "locked_until"])

    response = _login(client, user.email, PASSWORD)

    assert response.status_code == 302
    assert response.url == reverse("tasks:list")
    user.refresh_from_db()
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
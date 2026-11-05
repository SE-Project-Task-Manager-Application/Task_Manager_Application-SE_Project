from datetime import UTC, datetime

import pytest
from django.urls import reverse

from adminpanel.models import AuditRecord
from adminpanel.services import AuditService


pytestmark = pytest.mark.django_db


def test_admin_can_search_audit_entries_by_actor_action_and_target(client, make_user):
    admin = make_user(role="admin")
    actor = make_user(email="actor@example.com")
    AuditService.record(
        actor,
        "user.disabled",
        ("user", "4242"),
        timestamp=datetime(2026, 11, 4, 10, 30, tzinfo=UTC),
        details={"reason": "security review"},
    )
    AuditService.record(admin, "task.created", ("task", "9001"))
    client.force_login(admin)

    response = client.get(reverse("adminpanel:audit_log"), {"q": "actor@example.com"})

    assert response.status_code == 200
    assert b"actor@example.com" in response.content
    assert b"user.disabled" in response.content
    assert b"2026-11-04 10:30:00" in response.content
    assert b"4242" in response.content
    assert b"task.created" not in response.content

    response = client.get(reverse("adminpanel:audit_log"), {"q": "9001"})
    assert response.status_code == 200
    assert b"task.created" in response.content
    assert b"user.disabled" not in response.content


def test_member_cannot_view_audit_log(client, make_user):
    member = make_user(email="member@example.com")
    client.force_login(member)

    response = client.get(reverse("adminpanel:audit_log"))

    assert response.status_code == 403


def test_anonymous_user_is_redirected_from_audit_log(client):
    response = client.get(reverse("adminpanel:audit_log"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_audit_log_route_does_not_allow_writes(client, make_user):
    admin = make_user(role="admin")
    client.force_login(admin)

    response = client.post(reverse("adminpanel:audit_log"))

    assert response.status_code == 405
    assert not AuditRecord.objects.exists()

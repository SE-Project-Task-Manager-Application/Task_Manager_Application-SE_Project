import pytest
from django.test import Client
from django.urls import reverse

from adminpanel.models import AuditRecord


TEST_PASSWORD = "SEPROG123"
ADMIN_ACTIONS = ("disable_user", "enable_user", "delete_user")


def test_admin_can_view_users(client, make_user):
    admin = make_user(role="admin")
    make_user(email="member@example.com")

    client.force_login(admin)
    response = client.get(reverse("adminpanel:user_list"))

    assert response.status_code == 200
    assert b"member@example.com" in response.content
    assert b"Skip to main content" in response.content


def test_regular_user_cannot_view_user_list(client, make_user):
    member = make_user(email="member@example.com")

    client.force_login(member)
    response = client.get(reverse("adminpanel:user_list"))

    assert response.status_code == 403


def test_anonymous_user_is_redirected_to_login(client):
    response = client.get(reverse("adminpanel:user_list"))

    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


@pytest.mark.parametrize("action", ADMIN_ACTIONS)
def test_team_member_cannot_change_users(client, make_user, action):
    member = make_user(email="member@example.com")
    target = make_user(email="target@example.com")
    original_active = target.is_active
    original_deleted_at = target.deleted_at
    client.force_login(member)

    response = client.post(reverse(f"adminpanel:{action}", args=[target.pk]))

    assert response.status_code == 403
    target.refresh_from_db()
    assert target.is_active == original_active
    assert target.deleted_at == original_deleted_at
    assert not AuditRecord.objects.filter(target_id=str(target.pk)).exists()


def test_admin_cannot_disable_or_delete_themselves(client, make_user):
    admin = make_user(role="admin")
    client.force_login(admin)

    for action, expected_message in (
        ("disable_user", "cannot disable your own account"),
        ("delete_user", "cannot delete your own account"),
    ):
        response = client.post(reverse(f"adminpanel:{action}", args=[admin.pk]))
        assert response.status_code == 302
        assert response.url == reverse("adminpanel:user_list")
        assert any(
            expected_message in str(message).lower()
            for message in response.wsgi_request._messages
        )

    admin.refresh_from_db()
    assert admin.is_active
    assert admin.deleted_at is None
    assert not AuditRecord.objects.filter(target_id=str(admin.pk)).exists()


def test_disable_blocks_login_and_existing_session_and_enable_is_audited(client, make_user):
    admin = make_user(role="admin")
    member = make_user(email="member@example.com")
    member_client = Client()
    member_client.force_login(member)
    login_client = Client()
    client.force_login(admin)

    response = client.post(reverse("adminpanel:disable_user", args=[member.pk]))
    assert response.status_code == 302

    member.refresh_from_db()
    assert not member.is_active
    assert AuditRecord.objects.filter(
        action="user.disabled",
        target_type="user",
        target_id=str(member.pk),
    ).exists()

    # A session issued before the disable no longer grants access.
    response = member_client.get(reverse("adminpanel:user_list"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]

    response = login_client.post(
        reverse("accounts:login"),
        {"username": member.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in login_client.session

    response = client.post(reverse("adminpanel:enable_user", args=[member.pk]))
    assert response.status_code == 302
    assert AuditRecord.objects.filter(
        action="user.enabled",
        target_type="user",
        target_id=str(member.pk),
    ).exists()

    response = login_client.post(
        reverse("accounts:login"),
        {"username": member.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    assert str(member.pk) == login_client.session["_auth_user_id"]


def test_delete_soft_deletes_user_and_records_audit(client, make_user):
    admin = make_user(role="admin")
    member = make_user(email="member@example.com")
    client.force_login(admin)

    response = client.post(reverse("adminpanel:delete_user", args=[member.pk]))

    assert response.status_code == 302
    member.refresh_from_db()
    assert not member.is_active
    assert member.deleted_at is not None
    assert AuditRecord.objects.filter(
        action="user.deleted",
        target_type="user",
        target_id=str(member.pk),
    ).exists()

    response = client.get(reverse("adminpanel:user_list"))
    assert not response.context["users"].filter(pk=member.pk).exists()

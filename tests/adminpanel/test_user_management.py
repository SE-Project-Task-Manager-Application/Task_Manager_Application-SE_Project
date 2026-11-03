from django.urls import reverse

from adminpanel.models import AuditRecord


TEST_PASSWORD = "SEPROG123"


def test_admin_can_view_users(client, make_user):
    admin = make_user(role="admin")
    member = make_user(email="member@example.com")

    client.force_login(admin)
    response = client.get(reverse("adminpanel:user_list"))

    assert response.status_code == 200
    assert b"member@example.com" in response.content


def test_regular_user_cannot_view_user_list(client, make_user):
    member = make_user(email="member@example.com")

    client.force_login(member)
    response = client.get(reverse("adminpanel:user_list"))

    assert response.status_code == 403


def test_disable_blocks_login_and_enable_restores_it(client, make_user):
    admin = make_user(role="admin")
    member = make_user(email="member@example.com")
    client.force_login(admin)

    response = client.post(
        reverse("adminpanel:disable_user", args=[member.pk])
    )
    assert response.status_code == 302

    member.refresh_from_db()
    assert not member.is_active
    assert AuditRecord.objects.filter(
        action="user.disabled",
        target_type="user",
        target_id=str(member.pk),
    ).exists()

    client.logout()
    response = client.post(
        reverse("accounts:login"),
        {"username": member.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session

    client.force_login(admin)
    response = client.post(
        reverse("adminpanel:enable_user", args=[member.pk])
    )
    assert response.status_code == 302

    client.logout()
    response = client.post(
        reverse("accounts:login"),
        {"username": member.email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    assert str(member.pk) == client.session["_auth_user_id"]


def test_delete_soft_deletes_user_and_records_audit(client, make_user):
    admin = make_user(role="admin")
    member = make_user(email="member@example.com")
    client.force_login(admin)

    response = client.post(
        reverse("adminpanel:delete_user", args=[member.pk])
    )

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
    assert b"member@example.com" not in response.content

"""TC-Sec-03: task access is limited to owners and assignees."""

import pytest
from django.urls import reverse

from tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("route_name", ["delete", "complete", "reopen", "restore"])
def test_stranger_cannot_post_task_lifecycle_actions(client, make_user, route_name):
    owner, stranger = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Private")
    if route_name == "restore":
        task.soft_delete()
    client.force_login(stranger)

    response = client.post(
        reverse(f"tasks:{route_name}", args=[task.pk]),
        {"expected_version": task.version},
    )

    assert response.status_code == 403
    task.refresh_from_db()
    assert task.title == "Private"
    assert task.deleted_at is None if route_name != "restore" else task.deleted_at is not None


def test_anonymous_lifecycle_post_redirects_to_login(client, make_user):
    task = Task.objects.create(owner=make_user(), title="Private")
    response = client.post(
        reverse("tasks:complete", args=[task.pk]),
        {"expected_version": task.version},
    )
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/?next=")


def test_admin_has_no_special_access_to_another_users_task(client, make_user):
    owner, admin = make_user(), make_user("admin")
    task = Task.objects.create(owner=owner, title="Private")
    client.force_login(admin)

    assert client.get(reverse("tasks:edit", args=[task.pk])).status_code == 403
    assert "Private" not in client.get(reverse("tasks:list")).content.decode()

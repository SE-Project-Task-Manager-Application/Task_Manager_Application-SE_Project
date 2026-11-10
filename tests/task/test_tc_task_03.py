"""TC-Task-03: restoring soft-deleted tasks."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task

pytestmark = pytest.mark.django_db


def test_owner_can_restore_through_route(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Recoverable", deleted_at=timezone.now())
    client.force_login(owner)

    response = client.post(
        reverse("tasks:restore", args=[task.pk]),
        {"expected_version": task.version},
        follow=True,
    )

    assert response.status_code == 200
    assert Task.objects.get(pk=task.pk).deleted_at is None
    assert "Task restored." in response.content.decode()


def test_expired_restore_shows_message(client, make_user):
    owner = make_user()
    task = Task.objects.create(
        owner=owner,
        title="Expired",
        deleted_at=timezone.now() - timedelta(days=31),
    )
    client.force_login(owner)

    response = client.post(
        reverse("tasks:restore", args=[task.pk]),
        {"expected_version": task.version},
        follow=True,
    )

    assert response.status_code == 200
    assert "restored within 30 days" in response.content.decode()
    assert Task.objects.get(pk=task.pk).is_deleted


def test_owner_delete_removes_task_from_every_list(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Deleted everywhere")
    client.force_login(owner)

    response = client.post(
        reverse("tasks:delete", args=[task.pk]),
        {"expected_version": task.version},
        follow=True,
    )

    assert response.status_code == 200
    assert "Deleted everywhere" not in response.content.decode()
    assert "Deleted everywhere" not in client.get(
        reverse("tasks:list"), {"show": "all"}
    ).content.decode()
    assert "Deleted everywhere" in client.get(
        reverse("tasks:list"), {"show": "deleted"}
    ).content.decode()

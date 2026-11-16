"""Task-list links must respect the existing active-only detail route."""

import pytest
from django.urls import reverse

from collab.models import TaskShare
from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("role", ["owner", "assignee"])
def test_deleted_row_has_no_dead_detail_link_but_keeps_recovery_controls(client, make_user, role):
    owner, assignee = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Deleted task actions")
    TaskAssignment.objects.create(task=task, user=assignee, assigned_by=owner)
    task.soft_delete()
    client.force_login(owner if role == "owner" else assignee)
    detail_url = reverse("tasks:detail", args=[task.pk])

    response = client.get(reverse("tasks:list"), {"show": "deleted"})

    assert response.status_code == 200
    html = response.content.decode()
    assert task.title in html
    assert f'href="{detail_url}"' not in html
    assert reverse("collab:task_activity", args=[task.pk]) in html
    restore_url = reverse("tasks:restore", args=[task.pk])
    assert (f'action="{restore_url}"' in html) == (role == "owner")
    assert client.get(detail_url).status_code == 404


@pytest.mark.parametrize("role", ["owner", "assignee", "viewer", "editor"])
def test_live_row_keeps_working_detail_link_and_restore_brings_it_back(client, make_user, role):
    owner, other = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Live task actions")
    if role == "assignee":
        TaskAssignment.objects.create(task=task, user=other, assigned_by=owner)
    elif role in {"viewer", "editor"}:
        TaskShare.objects.create(task=task, user=other, shared_by=owner, permission=role)
    client.force_login(owner if role == "owner" else other)
    detail_url = reverse("tasks:detail", args=[task.pk])

    for show in ["active", "all"]:
        response = client.get(reverse("tasks:list"), {"show": show})
        assert response.status_code == 200
        assert f'href="{detail_url}"' in response.content.decode()
        assert client.get(detail_url).status_code == 200

    if role == "owner":
        task.soft_delete()
        task.refresh_from_db()
        response = client.post(
            reverse("tasks:restore", args=[task.pk]),
            {"expected_version": task.version},
            follow=True,
        )
        assert response.status_code == 200
        assert f'href="{detail_url}"' in response.content.decode()
        assert client.get(detail_url).status_code == 200

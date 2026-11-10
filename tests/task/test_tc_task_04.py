"""TC-Task-04: task lifecycle controls and list reachability."""

import pytest
from django.urls import reverse

from tasks.models import Task

pytestmark = pytest.mark.django_db


def test_bad_query_values_return_ok(client, make_user):
    owner = make_user()
    client.force_login(owner)
    response = client.get(reverse("tasks:list"), {"due_date": "abc", "sort": "bogus"})
    assert response.status_code == 200


def test_pagination_done_tasks_and_deleted_task_controls(client, make_user):
    owner, stranger = make_user(), make_user()
    for index in range(21):
        Task.objects.create(owner=owner, title=f"Task {index}")
    done = Task.objects.create(owner=owner, title="Done", status=Task.Status.DONE)
    deleted = Task.objects.create(owner=owner, title="Deleted")
    deleted.soft_delete()
    client.force_login(owner)

    page_two = client.get(reverse("tasks:list"), {"page": 2})
    assert page_two.status_code == 200
    assert "Task 0" in page_two.content.decode()

    all_tasks = client.get(reverse("tasks:list"), {"show": "all"}).content.decode()
    assert "Done" in all_tasks and reverse("tasks:reopen", args=[done.pk]) in all_tasks

    deleted_tasks = client.get(reverse("tasks:list"), {"show": "deleted"}).content.decode()
    assert "Deleted" in deleted_tasks
    assert reverse("tasks:restore", args=[deleted.pk]) in deleted_tasks

    client.force_login(stranger)
    stranger_deleted = client.get(reverse("tasks:list"), {"show": "deleted"}).content.decode()
    assert ">Deleted<" not in stranger_deleted
    assert reverse("tasks:restore", args=[deleted.pk]) not in stranger_deleted


def test_complete_hides_task_and_reopen_restores_it_to_default_list(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Lifecycle")
    client.force_login(owner)

    response = client.post(
        reverse("tasks:complete", args=[task.pk]),
        {"expected_version": task.version},
        follow=True,
    )
    assert response.status_code == 200
    assert "Lifecycle" not in response.content.decode()

    task.refresh_from_db()
    response = client.post(
        reverse("tasks:reopen", args=[task.pk]),
        {"expected_version": task.version},
        follow=True,
    )
    assert response.status_code == 200
    assert "Lifecycle" in response.content.decode()

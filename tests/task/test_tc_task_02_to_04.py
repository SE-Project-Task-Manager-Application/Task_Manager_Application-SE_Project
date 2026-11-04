"""TC-Task-02 to TC-Task-04 and TC-Sec-03 task lifecycle coverage."""

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import AuditRecord
from tasks.models import Label, Task, TaskAssignment
from tasks.services import StaleTaskError, TaskService

pytestmark = pytest.mark.django_db


def test_editor_can_update_every_task_field_and_increments_version(make_user):
    owner = make_user()
    label = Label.objects.create(name="urgent")
    task = Task.objects.create(owner=owner, title="old")

    updated = TaskService.update(
        owner,
        task,
        expected_version=1,
        title="new",
        description="details",
        priority=Task.Priority.HIGH,
        status=Task.Status.IN_PROGRESS,
        labels=[label],
    )

    assert updated.title == "new"
    assert updated.version == 2
    assert list(updated.labels.all()) == [label]
    assert AuditRecord.objects.filter(action="task.updated").exists()


def test_stale_update_is_rejected_without_overwriting(make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="original")
    TaskService.update(owner, task, expected_version=1, title="first")

    with pytest.raises(StaleTaskError):
        TaskService.update(owner, task, expected_version=1, title="stale")
    task.refresh_from_db()
    assert task.title == "first" and task.version == 2


def test_only_owner_can_delete_and_restore_within_retention(make_user):
    owner, other = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="recoverable")
    with pytest.raises(PermissionDenied):
        TaskService.delete(other, task)

    TaskService.delete(owner, task, expected_version=1)
    assert Task.objects.deleted().get(pk=task.pk).deleted_at is not None
    TaskService.restore(owner, task, expected_version=2)
    assert Task.objects.get(pk=task.pk).deleted_at is None


def test_deleted_task_cannot_be_restored_after_30_days(make_user):
    owner = make_user()
    task = Task.objects.create(
        owner=owner, title="expired", deleted_at=timezone.now() - timedelta(days=31)
    )
    with pytest.raises(ValidationError):
        TaskService.restore(owner, task)


def test_editor_can_complete_and_reopen(make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="status")
    TaskService.set_status(owner, task, Task.Status.DONE, expected_version=1)
    task.refresh_from_db()
    assert task.status == Task.Status.DONE and task.version == 2
    TaskService.set_status(owner, task, Task.Status.TODO, expected_version=2)
    assert Task.objects.get(pk=task.pk).status == Task.Status.TODO


def test_unrelated_user_gets_no_task_access(make_user):
    owner, stranger = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="private")
    with pytest.raises(PermissionDenied):
        TaskService.update(stranger, task, title="changed")
    with pytest.raises(PermissionDenied):
        TaskService.set_status(stranger, task, Task.Status.DONE)


def test_assigned_user_can_edit_task(make_user):
    owner, editor = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="shared")
    TaskAssignment.objects.create(task=task, user=editor, assigned_by=owner)
    TaskService.update(editor, task, title="edited")
    assert Task.objects.get(pk=task.pk).title == "edited"


def test_task_list_filters_and_hides_completed_tasks(client, make_user):
    owner = make_user()
    client.force_login(owner)
    Task.objects.create(owner=owner, title="urgent report", priority=Task.Priority.HIGH)
    Task.objects.create(owner=owner, title="done report", status=Task.Status.DONE)
    response = client.get(reverse("tasks:list"), {"q": "urgent", "priority": "high"})
    assert response.status_code == 200
    assert "urgent report" in response.content.decode()
    assert "done report" not in response.content.decode()


def test_task_lifecycle_routes_enforce_authorization_and_update_state(client, make_user):
    owner, stranger = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="route task")
    client.force_login(stranger)
    assert client.get(reverse("tasks:edit", args=[task.pk])).status_code == 403
    client.force_login(owner)
    response = client.post(
        reverse("tasks:complete", args=[task.pk]), {"expected_version": task.version}
    )
    assert response.status_code == 302
    assert Task.objects.get(pk=task.pk).status == Task.Status.DONE

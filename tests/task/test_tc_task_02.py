"""TC-Task-02: stale-safe task editing and assignment changes."""

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse

from adminpanel.models import AuditRecord
from tasks.models import Label, Task, TaskAssignment
from tasks.services import TaskService

pytestmark = pytest.mark.django_db


def test_stale_edit_through_form_shows_error_and_missing_version_is_rejected(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Original")
    client.force_login(owner)

    stale = client.post(
        reverse("tasks:edit", args=[task.pk]),
        {"title": "Changed", "priority": "medium", "status": "todo", "expected_version": "0"},
    )
    assert stale.status_code == 200
    assert "changed by someone else" in stale.content.decode()

    missing = client.post(
        reverse("tasks:edit", args=[task.pk]),
        {"title": "Changed", "priority": "medium", "status": "todo"},
    )
    assert missing.status_code == 200
    assert "This field is required." in missing.content.decode()
    assert Task.objects.get(pk=task.pk).title == "Original"


def test_pm_edit_keeps_existing_assignment_and_only_notifies_new_assignee(
    client, make_user, django_capture_on_commit_callbacks
):
    pm, first, second = (
        make_user("project_manager"),
        make_user(),
        make_user(),
    )
    task = Task.objects.create(owner=pm, title="Delegated")
    existing = TaskAssignment.objects.create(task=task, user=first, assigned_by=pm)
    client.force_login(pm)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("tasks:edit", args=[task.pk]),
            {
                "title": "Updated",
                "priority": "medium",
                "status": "todo",
                "expected_version": task.version,
                "assignees": [first.pk, second.pk],
            },
        )

    assert response.status_code == 302
    assert [message.to for message in mail.outbox] == [[second.email]]
    retained = TaskAssignment.objects.get(task=task, user=first)
    assert retained.assigned_by_id == existing.assigned_by_id
    assert retained.assigned_at == existing.assigned_at
    assert TaskAssignment.objects.filter(task=task, user=second).exists()

    task.refresh_from_db()
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("tasks:edit", args=[task.pk]),
            {
                "title": "Updated again",
                "priority": "medium",
                "status": "todo",
                "expected_version": task.version,
                "assignees": [first.pk],
            },
        )

    assert response.status_code == 302
    assert [message.to for message in mail.outbox] == [[second.email]]
    assert not TaskAssignment.objects.filter(task=task, user=second).exists()
    assert AuditRecord.objects.filter(
        action="task.assignee_removed", target_id=str(task.pk), details={"assignee_id": second.pk}
    ).exists()
    assert AuditRecord.objects.filter(action="task.assignee_added").count() == 1


def test_edit_preserves_existing_archived_label_but_rejects_new_archived_label(make_user):
    owner = make_user()
    kept = Label.objects.create(name="Legacy", is_archived=True)
    new_archived = Label.objects.create(name="Closed", is_archived=True)
    task = Task.objects.create(owner=owner, title="Tagged")
    task.labels.add(kept)

    TaskService.update(owner, task, expected_version=1, title="Retagged", labels=[kept])
    assert list(task.labels.values_list("pk", flat=True)) == [kept.pk]

    with pytest.raises(ValidationError) as error:
        TaskService.update(owner, task, expected_version=2, labels=[kept, new_archived])
    assert "archived" in str(error.value).lower()

"""TC-Collab-02: notify collaborators after a shared task is updated."""

import pytest
from django.core import mail
from django.core.management import call_command

from collab.models import TaskShare
from notif.models import Notification
from tasks.models import Task
from tasks.services import TaskService

pytestmark = pytest.mark.django_db


def test_shared_task_update_queues_all_other_collaborators(
    make_user, django_capture_on_commit_callbacks
):
    owner, editor, viewer = make_user(), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Shared report")
    TaskShare.objects.create(task=task, user=editor, permission="editor", shared_by=owner)
    TaskShare.objects.create(task=task, user=viewer, permission="viewer", shared_by=owner)

    with django_capture_on_commit_callbacks(execute=True):
        TaskService.update(editor, task, title="Updated report")

    queued = list(Notification.objects.order_by("recipient_id"))
    assert {item.recipient_id for item in queued} == {owner.pk, viewer.pk}
    assert all(item.kind == "task.shared_updated" for item in queued)
    assert all(item.status == Notification.Status.PENDING for item in queued)
    assert mail.outbox == []


def test_delivery_failure_stays_pending_and_a_later_run_retries(
    make_user, django_capture_on_commit_callbacks, monkeypatch
):
    owner, collaborator = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Shared report")
    TaskShare.objects.create(task=task, user=collaborator, permission="editor", shared_by=owner)
    with django_capture_on_commit_callbacks(execute=True):
        TaskService.update(owner, task, title="Updated report")

    monkeypatch.setattr(
        "notif.services.send_mail", lambda *args, **kwargs: (_ for _ in ()).throw(OSError())
    )
    call_command("deliver_notifications")
    notice = Notification.objects.get()
    assert notice.status == Notification.Status.PENDING
    assert notice.attempts == 1

    monkeypatch.setattr("notif.services.send_mail", lambda *args, **kwargs: 1)
    call_command("deliver_notifications")
    notice.refresh_from_db()
    assert notice.status == Notification.Status.SENT
    assert notice.attempts == 2

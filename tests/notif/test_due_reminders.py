from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from notif.models import Notification
from notif.services import NotificationService
from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db


def _task(owner, due_date, **kwargs):
    return Task.objects.create(owner=owner, title="Submit report", due_date=due_date, **kwargs)


def test_scheduler_queues_one_reminder_per_assignee_and_is_idempotent(make_user):
    now = timezone.now()
    owner, assignee, second = make_user(), make_user(), make_user()
    task = _task(owner, now + timedelta(hours=12))
    TaskAssignment.objects.create(task=task, user=assignee, assigned_by=owner)
    TaskAssignment.objects.create(task=task, user=second, assigned_by=owner)

    assert NotificationService.enqueue_due_reminders(now) == 2
    assert NotificationService.enqueue_due_reminders(now) == 0
    reminders = list(Notification.objects.order_by("recipient_id"))
    assert {item.recipient_id for item in reminders} == {assignee.pk, second.pk}
    assert all(item.scheduled_for == task.due_date - timedelta(hours=24) for item in reminders)


def test_unassigned_task_reminds_owner_and_not_early(make_user):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=30))
    assert NotificationService.enqueue_due_reminders(now) == 0

    task = Task.objects.get()
    task.due_date = now + timedelta(hours=23)
    task.save(update_fields=["due_date"])
    assert NotificationService.enqueue_due_reminders(now) == 1
    reminder = Notification.objects.get()
    assert reminder.recipient_id == owner.pk
    assert reminder.scheduled_for <= now


def test_delivery_failure_is_persisted_and_next_run_retries(make_user, monkeypatch):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)

    def unavailable(*args, **kwargs):
        raise OSError("mail server unavailable")

    monkeypatch.setattr("notif.services.send_mail", unavailable)
    assert NotificationService.deliver_scheduled(now) == (0, 1, 0)
    reminder = Notification.objects.get()
    assert reminder.status == Notification.Status.PENDING
    assert reminder.attempts == 1
    assert reminder.last_error == "delivery_failed"

    monkeypatch.setattr("notif.services.send_mail", lambda *args, **kwargs: 1)
    later = now + timedelta(minutes=1)
    assert NotificationService.deliver_scheduled(later) == (1, 0, 0)
    reminder.refresh_from_db()
    assert reminder.status == Notification.Status.SENT
    assert reminder.attempts == 2
    assert reminder.sent_at == later


def test_completed_or_rescheduled_task_cancels_outdated_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    task.status = Task.Status.DONE
    task.save(update_fields=["status"])

    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert Notification.objects.get().status == Notification.Status.CANCELLED
    assert mail.outbox == []


def test_management_command_queues_and_delivers_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=24))
    output = StringIO()

    call_command("send_due_reminders", stdout=output)

    reminder = Notification.objects.get()
    assert reminder.status == Notification.Status.SENT
    assert len(mail.outbox) == 1
    assert "Queued 1; sent 1" in output.getvalue()

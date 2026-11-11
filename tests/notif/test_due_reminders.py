from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Event, Lock

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from notif.models import Notification
from notif.services import NotificationService
from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db


def _task(owner, due_date, **kwargs):
    title = kwargs.pop("title", "Submit report")
    return Task.objects.create(owner=owner, title=title, due_date=due_date, **kwargs)


def _mail_server_down(*args, **kwargs):
    raise OSError("mail server unavailable")


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

    monkeypatch.setattr("notif.services.send_mail", _mail_server_down)
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


def test_runner_stops_after_first_mail_failure(make_user, monkeypatch):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=24), title="First")
    _task(owner, now + timedelta(hours=24), title="Second")
    NotificationService.enqueue_due_reminders(now)
    monkeypatch.setattr("notif.services.send_mail", _mail_server_down)

    assert NotificationService.deliver_scheduled(now) == (0, 1, 0)
    assert Notification.objects.filter(attempts=1).count() == 1
    assert Notification.objects.filter(attempts=0, status=Notification.Status.PENDING).count() == 1


def test_runner_caps_successful_deliveries_per_run(make_user, monkeypatch):
    now = timezone.now()
    owner = make_user()
    for index in range(NotificationService.MAX_DELIVERIES_PER_RUN + 1):
        _task(owner, now + timedelta(hours=24), title=f"Task {index}")
    NotificationService.enqueue_due_reminders(now)
    monkeypatch.setattr("notif.services.send_mail", lambda *args, **kwargs: 1)

    assert NotificationService.deliver_scheduled(now) == (
        NotificationService.MAX_DELIVERIES_PER_RUN, 0, 0
    )
    assert Notification.objects.filter(status=Notification.Status.SENT).count() == (
        NotificationService.MAX_DELIVERIES_PER_RUN
    )
    assert Notification.objects.filter(status=Notification.Status.PENDING).count() == 1


def test_delivery_stops_retrying_after_maximum_attempts(make_user, monkeypatch):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    monkeypatch.setattr("notif.services.send_mail", _mail_server_down)

    for attempt in range(NotificationService.MAX_ATTEMPTS):
        assert NotificationService.deliver_scheduled(now) == (0, 1, 0)
        reminder = Notification.objects.get()
        assert reminder.attempts == attempt + 1

    assert reminder.status == Notification.Status.FAILED
    assert NotificationService.deliver_scheduled(now) == (0, 0, 0)


def test_completed_task_cancels_and_reopened_task_requeues_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    task.status = Task.Status.DONE
    task.save(update_fields=["status"])

    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert Notification.objects.get().status == Notification.Status.CANCELLED
    assert mail.outbox == []

    task.status = Task.Status.TODO
    task.save(update_fields=["status"])
    assert NotificationService.enqueue_due_reminders(now) == 1
    assert NotificationService.deliver_scheduled(now) == (1, 0, 0)
    reminder = Notification.objects.get()
    assert reminder.status == Notification.Status.SENT
    assert reminder.attempts == 1
    assert len(mail.outbox) == 1


def test_soft_deleted_task_cancels_and_recovered_task_requeues_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    task.soft_delete()

    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert Notification.objects.get().status == Notification.Status.CANCELLED

    task.deleted_at = None
    task.save(update_fields=["deleted_at"])
    assert NotificationService.enqueue_due_reminders(now) == 1
    assert NotificationService.deliver_scheduled(now) == (1, 0, 0)
    assert Notification.objects.get().status == Notification.Status.SENT


def test_rescheduled_task_cancels_old_and_queues_new_due_date(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    old_due_date = task.due_date
    NotificationService.enqueue_due_reminders(now)

    task.due_date = now + timedelta(hours=23)
    task.save(update_fields=["due_date"])
    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert NotificationService.enqueue_due_reminders(now) == 1
    assert Notification.objects.count() == 2
    old_reminder = Notification.objects.get(task_due_date=old_due_date)
    new_reminder = Notification.objects.get(task_due_date=task.due_date)
    assert old_reminder.status == Notification.Status.CANCELLED
    assert new_reminder.status == Notification.Status.PENDING


def test_changing_due_date_back_revives_cancelled_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    original_due_date = task.due_date
    NotificationService.enqueue_due_reminders(now)

    task.due_date = now + timedelta(hours=23)
    task.save(update_fields=["due_date"])
    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert NotificationService.enqueue_due_reminders(now) == 1

    task.due_date = original_due_date
    task.save(update_fields=["due_date"])
    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert NotificationService.enqueue_due_reminders(now) == 1
    assert Notification.objects.count() == 2
    revived = Notification.objects.get(task_due_date=original_due_date)
    assert revived.status == Notification.Status.PENDING
    assert revived.attempts == 0


def test_overdue_task_cancels_pending_reminder(make_user):
    now = timezone.now()
    owner = make_user()
    task = _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    task.due_date = now - timedelta(seconds=1)
    task.save(update_fields=["due_date"])

    assert NotificationService.deliver_scheduled(now) == (0, 0, 1)
    assert Notification.objects.get().status == Notification.Status.CANCELLED
    assert mail.outbox == []


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    connection.vendor != "postgresql", reason="row-lock behavior requires PostgreSQL"
)
def test_overlapping_runners_do_not_send_the_same_reminder(make_user, monkeypatch):
    now = timezone.now()
    owner = make_user()
    _task(owner, now + timedelta(hours=24))
    NotificationService.enqueue_due_reminders(now)
    send_started = Event()
    allow_send_to_finish = Event()
    calls = []
    calls_lock = Lock()

    def slow_send(*args, **kwargs):
        with calls_lock:
            calls.append(1)
        send_started.set()
        if not allow_send_to_finish.wait(timeout=5):
            raise TimeoutError("test did not release the first sender")
        return 1

    monkeypatch.setattr("notif.services.send_mail", slow_send)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(NotificationService.deliver_scheduled, now)
        assert send_started.wait(timeout=5)
        second = pool.submit(NotificationService.deliver_scheduled, now)
        try:
            assert second.result(timeout=5) == (0, 0, 0)
        finally:
            allow_send_to_finish.set()
        assert first.result(timeout=5) == (1, 0, 0)

    assert calls == [1]
    assert Notification.objects.get().status == Notification.Status.SENT


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

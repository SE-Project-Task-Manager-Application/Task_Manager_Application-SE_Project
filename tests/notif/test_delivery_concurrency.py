"""Concurrent notification workers must not send the same row twice."""

from threading import Event, Lock, Thread

import pytest
from django.db import connections
from django.utils import timezone

from notif.models import Notification
from notif.services import NotificationService
from tasks.models import Task

pytestmark = pytest.mark.django_db(transaction=True)


def _notice(owner, recipient, kind="task.shared_updated"):
    task = Task.objects.create(owner=owner, title="Concurrent delivery")
    return Notification.objects.create(
        kind=kind,
        recipient=recipient,
        task=task,
        subject="Task updated",
        body="The task changed.",
        scheduled_for=timezone.now(),
    )


def test_overlapping_shared_delivery_runs_send_each_notice_once(
    make_user, monkeypatch
):
    owner = make_user()
    notices = [_notice(owner, make_user()) for _ in range(3)]
    send_started = Event()
    allow_send_to_finish = Event()
    call_lock = Lock()
    send_calls = []
    results = []
    errors = []

    def slow_send(*args, **kwargs):
        with call_lock:
            send_calls.append((args, kwargs))
            first_call = len(send_calls) == 1
        if first_call:
            send_started.set()
            if not allow_send_to_finish.wait(timeout=5):
                raise TimeoutError("test did not release the first send")
        return 1

    monkeypatch.setattr("notif.services.send_mail", slow_send)

    def deliver():
        connections.close_all()
        try:
            results.append(NotificationService.deliver_persisted())
        except Exception as error:  # surfaced in the main test thread below
            errors.append(error)
        finally:
            connections.close_all()

    first = Thread(target=deliver)
    second = Thread(target=deliver)
    first.start()
    try:
        assert send_started.wait(timeout=5)
        second.start()
        second.join(timeout=5)
        assert not second.is_alive(), "the overlapping worker should skip the claimed row"
    finally:
        allow_send_to_finish.set()
    first.join(timeout=5)

    assert not first.is_alive()
    assert not errors
    assert len(send_calls) == 3
    assert sorted(results) == [(1, 0), (2, 0)]
    for notice in notices:
        notice.refresh_from_db()
        assert notice.status == Notification.Status.SENT
        assert notice.attempts == 1


def test_due_reminder_worker_does_not_consume_shared_update_notices(make_user, monkeypatch):
    owner, recipient = make_user(), make_user()
    notice = _notice(owner, recipient)
    send_calls = []
    monkeypatch.setattr("notif.services.send_mail", lambda *args, **kwargs: send_calls.append(args))

    assert NotificationService.deliver_scheduled() == (0, 0, 0)

    notice.refresh_from_db()
    assert notice.status == Notification.Status.PENDING
    assert notice.attempts == 0
    assert send_calls == []

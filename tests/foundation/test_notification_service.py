"""S-05: NotificationService stub."""

import pytest
from django.core import mail
from django.http import HttpResponse
from django.test import RequestFactory

from notif.services import NotificationEvent, NotificationService

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_queue():
    NotificationService.clear()
    yield
    NotificationService.clear()


def _event(user, kind="task.assigned"):
    return NotificationEvent(kind=kind, recipient=user, subject="Hello", body="Body text")


def test_enqueue_keeps_events_in_order(make_user):
    user = make_user()
    first, second = _event(user, "a.one"), _event(user, "a.two")
    NotificationService.enqueue(first)
    NotificationService.enqueue(second)
    assert NotificationService.pending() == [first, second]


def test_enqueue_rejects_other_objects():
    with pytest.raises(TypeError):
        NotificationService.enqueue("not an event")


def test_send_delivers_an_email(make_user):
    user = make_user()
    assert NotificationService.send(_event(user)) is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert mail.outbox[0].subject == "Hello"


def test_deliver_pending_empties_the_queue(make_user):
    user = make_user()
    NotificationService.enqueue(_event(user))
    NotificationService.enqueue(_event(user))
    assert NotificationService.deliver_pending() == (2, 0)
    assert NotificationService.pending() == []
    assert len(mail.outbox) == 2


def test_send_failure_is_contained_and_logged_safely(make_user, monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise ConnectionRefusedError("smtp://user:secret@mail.example:1025 refused")

    monkeypatch.setattr("notif.services.send_mail", boom)
    with caplog.at_level("WARNING"):
        assert NotificationService.send(_event(make_user())) is False
    assert "ConnectionRefusedError" in caplog.text
    assert "secret" not in caplog.text  # the exception message is not logged


def test_recipient_without_email_is_skipped(make_user):
    user = make_user()
    user.email = ""
    assert NotificationService.send(_event(user)) is False
    assert mail.outbox == []


def test_notification_service_can_be_called_from_a_view(make_user):
    """Done-when: callable from a view as well as from a test."""
    user = make_user()

    def view(request):
        NotificationService.send(_event(user))
        return HttpResponse("ok")

    assert view(RequestFactory().get("/")).status_code == 200
    assert len(mail.outbox) == 1

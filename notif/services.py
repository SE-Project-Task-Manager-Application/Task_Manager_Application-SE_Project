"""NotificationService (S-05): notification enqueue and delivery helpers.

Shared-task update events are persisted during the task update transaction, so a mail
server outage cannot affect that action and the event survives process restarts.

- send(event)           deliver one event now; returns True/False and never raises.
- enqueue(event)        queue an event for later delivery
- deliver_persisted()   attempt durable shared-task notices; failed rows remain pending.

Verify delivery by watching MailHog (http://localhost:8025) or, in tests, the
django.core.mail.outbox list.

Shared-task update notifications are retried by running the ``deliver_notifications``
management command every five minutes (TC-Collab-02).
"""

import logging
from collections import deque
from dataclasses import dataclass, field

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Notification

logger = logging.getLogger(__name__)

_pending = deque()


@dataclass(frozen=True)
class NotificationEvent:
    kind: str  # stable name such as "task.assigned"
    recipient: object  # a user with an e-mail address
    subject: str
    body: str
    context: dict = field(default_factory=dict)


class NotificationService:
    @staticmethod
    def enqueue_persisted(event, task):
        """Persist an event so a later delivery run can retry it."""
        if not isinstance(event, NotificationEvent):
            raise TypeError("enqueue_persisted() needs a NotificationEvent.")
        return Notification.objects.create(
            kind=event.kind,
            recipient=event.recipient,
            task=task,
            subject=event.subject,
            body=event.body,
            scheduled_for=timezone.now(),
        )

    @classmethod
    def deliver_persisted(cls, now=None):
        """Attempt all pending notifications; failures remain queued for retry."""
        now = now or timezone.now()
        sent = failed = 0
        pending = Notification.objects.filter(
            status=Notification.Status.PENDING, scheduled_for__lte=now
        ).select_related("recipient")
        for notification in pending.iterator():
            notification.attempts += 1
            notification.last_attempt_at = now
            event = NotificationEvent(
                kind=notification.kind,
                recipient=notification.recipient,
                subject=notification.subject,
                body=notification.body,
            )
            if cls.send(event):
                notification.status = Notification.Status.SENT
                notification.sent_at = now
                notification.last_error = ""
                sent += 1
            else:
                notification.last_error = "delivery_failed"
                failed += 1
            notification.save(
                update_fields=["attempts", "last_attempt_at", "status", "sent_at", "last_error"]
            )
        return sent, failed

    @staticmethod
    def enqueue(event):
        """Queue an event for delivery and return it."""
        if not isinstance(event, NotificationEvent):
            raise TypeError("enqueue() needs a NotificationEvent.")
        _pending.append(event)
        return event

    @staticmethod
    def pending():
        """The events waiting for delivery, oldest first (a copy)."""
        return list(_pending)

    @staticmethod
    def clear():
        """Drop all queued events (used by tests)."""
        _pending.clear()

    @staticmethod
    def send(event):
        """Deliver one event by e-mail. True on success, False on failure; never raises."""
        recipient_email = getattr(event.recipient, "email", "")
        if not recipient_email:
            logger.warning("notification skipped kind=%s: recipient has no e-mail", event.kind)
            return False
        try:
            send_mail(
                event.subject,
                event.body,
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [recipient_email],
                fail_silently=False,
            )
        except Exception as exc:  # delivery problems must not break the caller
            # Log the exception type only: its message could echo connection details.
            logger.warning(
                "notification failed kind=%s recipient_id=%s error=%s",
                event.kind,
                getattr(event.recipient, "pk", None),
                type(exc).__name__,
            )
            return False
        return True

    @classmethod
    def deliver_pending(cls):
        """Send every queued event. Returns (sent_count, failed_count)."""
        sent = failed = 0
        while _pending:
            if cls.send(_pending.popleft()):
                sent += 1
            else:
                failed += 1
        return sent, failed

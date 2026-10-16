"""NotificationService (S-05): thin working stub for the notification interface.

SAD 4.3: NotificationService.enqueue/send(event) accepts a domain event and delivers
it. This stub keeps pending events in memory and sends them as e-mail through Django's
mail layer (MailHog in development). It is deliberately small:

- enqueue(event)        queue an event for later delivery
- send(event)           deliver one event now; returns True/False and never raises, so a
                        mail-server problem cannot break the request that triggered it
- deliver_pending()     send everything queued (for a later scheduled command)

Not done yet (later notification stories): a persisted Notification table that survives
restarts, retry/back-off, and due-date reminders. See DEVIATIONS.md.
"""

import logging
from collections import deque
from dataclasses import dataclass, field

from django.conf import settings
from django.core.mail import send_mail

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

"""Notification helpers for immediate mail and persistent scheduled reminders.

SAD 4.3: NotificationService.enqueue/send(event) accepts a domain event and delivers
it. Legacy ``enqueue()`` events are held in memory; scheduled task reminders are stored
in the database. E-mail is sent through Django's mail layer (MailHog in development):

- send(event)           deliver one event now; returns True/False and never raises, so a
                        mail-server problem cannot break the request that triggered it.
                        The connection times out after EMAIL_TIMEOUT seconds. This is
                        what TaskService calls (after commit) when a task is assigned.
- enqueue(event)        retain the legacy in-memory event queue
- deliver_pending()     deliver the legacy in-memory queue

Task due-date reminders use the persisted Notification model and are handled by the
``send_due_reminders`` management command.

Verify delivery by watching MailHog (http://localhost:8025) or, in tests, the
django.core.mail.outbox list.

"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone

from tasks.models import Task
from .models import Notification

from adminpanel.config import get_system_config

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
    REMINDER_LEAD = timedelta(hours=24)
    MAX_DELIVERIES_PER_RUN = 5
    # At the documented one-minute scheduler interval this allows up to two hours
    # of retries before a persistently undeliverable reminder becomes terminal.
    MAX_ATTEMPTS = 120

    @classmethod
    def enqueue_due_reminders(cls, now=None):
        """Persist reminders for open tasks due within the next 24 hours.

        Repeated scheduler runs are idempotent. Tasks without assignees notify owners.
        """
        now = now or timezone.now()
        cutoff = now + cls.REMINDER_LEAD
        tasks = Task.objects.active().exclude(status=Task.Status.DONE).filter(
            due_date__gt=now, due_date__lte=cutoff
        ).prefetch_related("assignments__user")
        created = 0
        for task in tasks:
            due_date = task.due_date
            assignees = [assignment.user for assignment in task.assignments.all()]
            for recipient in assignees or [task.owner]:
                try:
                    with transaction.atomic():
                        reminder_rows = Notification.objects.select_for_update()
                        notification, was_created = reminder_rows.get_or_create(
                            task=task,
                            recipient=recipient,
                            kind="task.due_reminder",
                            task_due_date=due_date,
                            defaults={
                                "subject": f"Reminder: {task.title} is due soon",
                                "body": (
                                    f"The task '{task.title}' is due at "
                                    f"{timezone.localtime(due_date):%Y-%m-%d %H:%M %Z}."
                                ),
                                "scheduled_for": due_date - cls.REMINDER_LEAD,
                            },
                        )
                        revived = False
                        if not was_created and notification.status == Notification.Status.CANCELLED:
                            notification.status = Notification.Status.PENDING
                            notification.attempts = 0
                            notification.last_attempt_at = None
                            notification.sent_at = None
                            notification.last_error = ""
                            notification.scheduled_for = due_date - cls.REMINDER_LEAD
                            notification.save(update_fields=[
                                "status", "attempts", "last_attempt_at", "sent_at",
                                "last_error", "scheduled_for",
                            ])
                            revived = True
                    created += int(was_created or revived)
                except IntegrityError:
                    # Concurrent scheduler instances can race on the unique reminder key.
                    continue
        return created

    @classmethod
    def deliver_scheduled(cls, now=None):
        """Deliver a bounded batch of due rows, locking each row against other runners.

        Failed mail remains pending for retry, but the run stops at the first failure
        and permanently fails a row after MAX_ATTEMPTS. A batch limit plus the SMTP
        timeout keeps an outage from making a minute scheduler run unbounded.
        """
        now = now or timezone.now()
        sent = failed = cancelled = 0
        processed = 0
        while processed < cls.MAX_DELIVERIES_PER_RUN:
            failed_this_attempt = False
            with transaction.atomic():
                notification = (
                    Notification.objects.filter(
                        status=Notification.Status.PENDING, scheduled_for__lte=now
                    )
                    .select_related("recipient", "task")
                    .select_for_update(skip_locked=True, of=("self",))
                    .order_by("scheduled_for", "pk")
                    .first()
                )
                if notification is None:
                    break

                task = notification.task
                if notification.kind == "task.due_reminder" and (
                    task is None
                    or task.is_deleted
                    or task.status == Task.Status.DONE
                    or task.due_date is None
                    or task.due_date <= now
                    or task.due_date != notification.task_due_date
                ):
                    notification.status = Notification.Status.CANCELLED
                    notification.save(update_fields=["status"])
                    cancelled += 1
                    processed += 1
                    continue

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
                    if notification.attempts >= cls.MAX_ATTEMPTS:
                        notification.status = Notification.Status.FAILED
                    failed += 1
                    failed_this_attempt = True
                notification.save(update_fields=[
                    "attempts", "last_attempt_at", "status", "sent_at", "last_error"
                ])
                processed += 1
            if failed_this_attempt:
                break
        return sent, failed, cancelled

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
        config = get_system_config()
        if not config.notifications_enabled:
            logger.info("notification disabled kind=%s", event.kind)
            return False
        try:
            sender = (
                config.notification_sender or getattr(settings, "DEFAULT_FROM_EMAIL", None)
            )
            send_mail(
                event.subject,
                event.body,
                sender,
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

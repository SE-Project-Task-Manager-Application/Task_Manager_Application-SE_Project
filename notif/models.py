"""Durable notification delivery state."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        CANCELLED = "cancelled", "Cancelled"

    kind = models.CharField(max_length=80)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task = models.ForeignKey(
        "tasks.Task",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    task_due_date = models.DateTimeField(null=True, blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "recipient", "kind", "task_due_date"],
                name="unique_task_reminder_per_due_date",
            ),
        ]
        indexes = [models.Index(fields=["status", "scheduled_for"])]

    def __str__(self):
        return f"{self.kind} to {self.recipient_id} ({self.status})"

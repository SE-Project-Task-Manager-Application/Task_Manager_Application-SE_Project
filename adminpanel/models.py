"""Append-only audit record (S-05), following docs/schema.md and SAD sections 4.3-4.4.

Audit rows can be created but never changed or removed through the ORM: save() on an
existing row, delete(), and the queryset update()/delete()/bulk_update() all raise.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditImmutableError(Exception):
    """Raised on any attempt to modify or delete an audit record."""


class AuditRecordQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise AuditImmutableError("Audit records are append-only.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise AuditImmutableError("Audit records are append-only.")

    def delete(self):
        raise AuditImmutableError("Audit records are append-only.")


class AuditRecord(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,  # empty for a system action
        on_delete=models.PROTECT,
        related_name="audit_records",
    )
    action = models.CharField(max_length=100, db_index=True)  # e.g. "task.created"
    target_type = models.CharField(max_length=50)  # e.g. "task"
    target_id = models.CharField(max_length=64)  # e.g. "42"
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    details = models.JSONField(default=dict, blank=True)  # never secrets

    objects = AuditRecordQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["target_type", "target_id"])]

    def __str__(self):
        return f"{self.action} on {self.target_type} {self.target_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutableError("Audit records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit records are append-only.")

"""Task data model (S-04), following docs/schema.md and SAD section 4.1.

Deliberate points:
- A task has one *owner* (the creator) and zero or more *assignees*. Assignees are
  stored in TaskAssignment rows, as agreed in the schema, not as a column on Task.
- Tasks are soft-deleted: `deleted_at` is set and the row is kept (30-day recovery,
  TM-F-012). Use Task.objects.active() for anything a user sees.
- `version` supports the stale-edit check in SAD section 4.4 (TM-NF-003).
"""

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Label(models.Model):
    """A label/category a task can carry (TM-F-020). Archived ones are hidden (TM-F-051)."""

    name = models.CharField(max_length=50)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="unique_label_name_ci"),
        ]

    def __str__(self):
        return self.name


class TaskQuerySet(models.QuerySet):
    def active(self):
        """Tasks that have not been soft-deleted."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Soft-deleted tasks (kept for recovery)."""
        return self.filter(deleted_at__isnull=False)


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # users are soft-deleted, never removed
        related_name="owned_tasks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateTimeField(null=True, blank=True)
    labels = models.ManyToManyField(Label, blank=True, related_name="tasks")
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TaskAssignment",
        through_fields=("task", "user"),
        related_name="assigned_tasks",
        blank=True,
    )
    version = models.PositiveIntegerField(default=1)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["deleted_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def soft_delete(self):
        """Mark the task deleted without removing the row. Callers handle audit/auth."""
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class TaskAssignment(models.Model):
    """One user assigned to one task, with who assigned them and when."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="task_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+"
    )
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["assigned_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["task", "user"], name="unique_task_assignment"),
        ]

    def __str__(self):
        return f"{self.user_id} on task {self.task_id}"

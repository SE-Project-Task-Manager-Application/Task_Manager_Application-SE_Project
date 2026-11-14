"""Collaboration data (CollabModule, SAD 4.1): task sharing (TM-F-030) and comments (TM-F-033)."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from tasks.models import Task

class TaskShare(models.Model):
    class Permission(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        EDITOR = "editor", "Editor"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="task_shares"
    )
    permission = models.CharField(max_length=10, choices=Permission.choices)
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_task_shares"
    )
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["shared_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["task", "user"], name="unique_task_share"),
        ]

    def __str__(self):
        return f"{self.user} ({self.get_permission_display()}) on {self.task}"


COMMENT_MAX_LENGTH = 2000


class Comment(models.Model):
    """One comment on a task, with its author and when it was posted.

    Comments are shown oldest first so a task reads as a conversation. Each new
    comment also writes a `task.commented` audit record, which the task activity
    history (TM-F-034) reads.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # users are soft-deleted, never removed
        related_name="task_comments",
    )
    body = models.TextField(max_length=COMMENT_MAX_LENGTH)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["task", "created_at"], name="collab_comm_task_id_6f1b2e_idx"),
        ]

    def __str__(self):
        return f"Comment {self.pk} on task {self.task_id}"

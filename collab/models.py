"""Collaboration data (CollabModule, SAD 4.1): task comments (TM-F-033)."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from tasks.models import Task

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

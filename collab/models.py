from django.conf import settings
from django.db import models

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

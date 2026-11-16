
from django.conf import settings
from django.db import models

from tasks.models import Task


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="task_attachments"
    )
    file = models.FileField(upload_to="task-attachments/")
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return self.original_name

"""Collaboration operations (CollabModule, SAD 4.1)."""

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.services import require_task_permission
from adminpanel.services import AuditService

from .models import COMMENT_MAX_LENGTH, Comment


class CommentService:
    @staticmethod
    @transaction.atomic
    def add(actor, task, body):
        """Add a comment to a task the actor can access (TM-F-033).

        Anyone who can view the task may comment; this reuses the central task
        permission check, so it follows any change to who can view a task (for
        example when sharing is added). The audit record is written in the same
        transaction (SAD 4.4) and feeds the task activity history (TM-F-034).
        """
        require_task_permission(actor, task, "view")
        if task.is_deleted:
            raise ValidationError("You cannot comment on a deleted task.")
        body = (body or "").strip()
        if not body:
            raise ValidationError("Write a comment before posting it.")
        if len(body) > COMMENT_MAX_LENGTH:
            raise ValidationError(
                f"A comment can be at most {COMMENT_MAX_LENGTH} characters."
            )
        comment = Comment.objects.create(task=task, author=actor, body=body)
        AuditService.record(
            actor,
            "task.commented",
            task,
            timestamp=comment.created_at,
            details={"comment_id": comment.pk},
        )
        return comment

    @staticmethod
    def for_task(actor, task):
        """Comments on a task, oldest first, for someone who can view the task."""
        require_task_permission(actor, task, "view")
        return Comment.objects.filter(task=task).select_related("author")

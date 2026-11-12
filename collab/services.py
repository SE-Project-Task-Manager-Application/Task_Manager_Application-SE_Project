"""Collaboration operations (CollabModule, SAD 4.1)."""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.services import require_task_permission
from adminpanel.services import AuditService
from tasks.models import Task

from .models import COMMENT_MAX_LENGTH, Comment, TaskShare


def _active(user):
    return bool(user and user.is_active and not getattr(user, "deleted_at", None))


class TaskShareService:
    @staticmethod
    @transaction.atomic
    def share(task, user, permission, actor):
        """Create or change a task share. Only the active owner can share a task."""
        if not _active(actor):
            raise PermissionDenied("Only an active task owner can share a task.")
        task = Task.objects.select_for_update().get(pk=task.pk)
        if task.owner_id != actor.pk:
            raise PermissionDenied("Only the task owner can share this task.")
        if task.is_deleted:
            raise ValidationError("A deleted task cannot be shared.")
        if not _active(user):
            raise ValidationError("That account is disabled and cannot receive a share.")
        if user.pk == actor.pk:
            raise ValidationError("You already have access as the task owner.")
        if permission not in TaskShare.Permission.values:
            raise ValidationError("Choose Viewer or Editor access.")

        share, created = TaskShare.objects.get_or_create(
            task=task,
            user=user,
            defaults={"permission": permission, "shared_by": actor},
        )
        changed = created or share.permission != permission
        if changed and not created:
            share.permission = permission
            share.shared_by = actor
            share.save(update_fields=["permission", "shared_by"])
        if changed:
            AuditService.record(
                actor,
                "task.shared" if created else "task.share_updated",
                task,
                details={"user_id": user.pk, "permission": permission},
            )
        return share


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

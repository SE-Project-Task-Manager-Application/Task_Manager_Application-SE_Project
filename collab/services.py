"""Collaboration operations (CollabModule, SAD 4.1)."""

from dataclasses import dataclass
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.services import require_task_permission
from adminpanel.models import AuditRecord
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

    @staticmethod
    @transaction.atomic
    def revoke(task, user, actor):
        """Remove a collaborator's access. Only the active task owner can revoke."""
        if not _active(actor):
            raise PermissionDenied("Only an active task owner can revoke task access.")
        task = Task.objects.select_for_update().get(pk=task.pk)
        if task.owner_id != actor.pk:
            raise PermissionDenied("Only the task owner can revoke task access.")

        share = TaskShare.objects.select_for_update().filter(task=task, user=user).first()
        if share is None:
            return False

        AuditService.record(
            actor,
            "task.share_revoked",
            task,
            details={"user_id": user.pk, "permission": share.permission},
        )
        share.delete()
        return True

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


@dataclass(frozen=True)
class ActivityEntry:
    """One line of a task's activity history (TM-F-034)."""

    timestamp: datetime
    actor: str
    action: str
    description: str


# Field names as people see them on the task form.
FIELD_LABELS = {
    "title": "title",
    "description": "description",
    "due_date": "due date",
    "priority": "priority",
    "labels": "labels",
}

COMMENT_EXCERPT_LENGTH = 80


class ActivityService:
    """Builds a task's chronological activity history from its audit records (TM-F-034).

    Every event is written through AuditService in the same transaction as the change
    (SAD 4.3/4.4), so the history is read straight from the audit log, oldest first,
    with UTC timestamps.
    """

    @staticmethod
    def for_task(actor, task):
        require_task_permission(actor, task, "view")
        records = list(
            AuditRecord.objects.filter(target_type="task", target_id=str(task.pk))
            .select_related("actor")
            .order_by("created_at", "id")
        )
        user_ids = set()
        comment_ids = set()
        for record in records:
            details = record.details or {}
            for key in ("assignee_id", "user_id"):
                if details.get(key) is not None:
                    user_ids.add(details[key])
            if record.action == "task.commented" and details.get("comment_id"):
                comment_ids.add(details["comment_id"])
        users = {user.pk: user.email for user in get_user_model().objects.filter(pk__in=user_ids)}
        comments = {
            comment.pk: comment.body
            for comment in Comment.objects.filter(pk__in=comment_ids, task=task)
        }
        return [
            ActivityEntry(
                timestamp=record.created_at,
                actor=record.actor.email if record.actor else "System",
                action=record.action,
                description=_describe(record, users, comments),
            )
            for record in records
        ]


def _status_label(value):
    return dict(Task.Status.choices).get(value, value or "unknown")


def _permission_label(value):
    return dict(TaskShare.Permission.choices).get(value, value or "unknown")


def _excerpt(text):
    text = " ".join((text or "").split())
    if len(text) <= COMMENT_EXCERPT_LENGTH:
        return text
    return text[: COMMENT_EXCERPT_LENGTH - 1].rstrip() + "…"


def _describe(record, users, comments):
    details = record.details or {}
    action = record.action

    def user(key):
        return users.get(details.get(key), "a user")

    permission = _permission_label(details.get("permission"))

    if action == "task.created":
        return "created the task"
    if action == "task.updated":
        fields = [FIELD_LABELS.get(field, field) for field in details.get("fields") or []]
        return f"edited the {', '.join(fields)}" if fields else "edited the task"
    if action == "task.status_changed":
        return (
            f"changed the status from {_status_label(details.get('from'))} "
            f"to {_status_label(details.get('to'))}"
        )
    if action == "task.assignee_added":
        return f"assigned {user('assignee_id')}"
    if action == "task.assignee_removed":
        return f"unassigned {user('assignee_id')}"
    if action == "task.commented":
        body = comments.get(details.get("comment_id"))
        return f"commented: “{_excerpt(body)}”" if body else "commented"
    if action == "task.shared":
        return f"shared the task with {user('user_id')} as {permission}"
    if action == "task.share_updated":
        return f"changed {user('user_id')}'s access to {permission}"
    if action == "task.share_revoked":
        return f"removed {user('user_id')}'s access"
    if action == "task.attachment_added":
        return f"attached {details.get('filename') or 'a file'}"
    if action == "task.deleted":
        return "deleted the task"
    if action == "task.restored":
        return "restored the task"
    return action.removeprefix("task.").replace("_", " ")

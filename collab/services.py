from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from adminpanel.services import AuditService
from tasks.models import Task

from .models import TaskShare


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

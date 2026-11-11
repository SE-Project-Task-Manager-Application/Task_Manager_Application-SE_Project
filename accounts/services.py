"""Central task authorization rules."""

from django.core.exceptions import PermissionDenied


def _active(user):
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and not getattr(user, "deleted_at", None)
    )


def can_view_task(actor, task):
    if not _active(actor):
        return False
    from tasks.models import Task

    return Task.objects.visible_to(actor).filter(pk=task.pk).exists()


def can_edit_task(actor, task):
    if not _active(actor):
        return False
    from tasks.models import Task

    return Task.objects.editable_by(actor).filter(pk=task.pk).exists()


def can_delete_task(actor, task):
    return _active(actor) and task.owner_id == actor.pk


def require_task_permission(actor, task, action="view"):
    checks = {
        "view": can_view_task,
        "edit": can_edit_task,
        "delete": can_delete_task,
    }
    try:
        allowed = checks[action](actor, task)
    except KeyError:
        raise ValueError(f"Unknown task permission: {action}") from None
    if not allowed:
        raise PermissionDenied("You do not have permission to perform this action.")

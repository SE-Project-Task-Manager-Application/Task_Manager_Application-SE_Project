"""TaskService (TM-F-010): business rules for tasks, kept out of the views (SAD 4.1, 4.3).

Only create() and assign() exist so far; update/delete/complete are added by the
stories for TM-F-011 to TM-F-013. Rules enforced here, not in the UI:
- assignment is restricted to the Project Manager role (SAD 4.3);
- a task and its audit record are written in one transaction (SAD 4.4);
- assignment notifies the assignee, but only once the transaction has committed.
"""

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from adminpanel.services import AuditService
from notif.services import NotificationEvent, NotificationService

from .models import Task, TaskAssignment

# Must match the role values in docs/schema.md.
ROLE_PROJECT_MANAGER = "project_manager"


def _is_active(user):
    return bool(user and user.is_active and not getattr(user, "deleted_at", None))


def _require_active_actor(actor):
    if not _is_active(actor):
        raise PermissionDenied("Only an active user can do this.")


def can_assign(actor):
    """Only a Project Manager may assign tasks."""
    return _is_active(actor) and getattr(actor, "role", None) == ROLE_PROJECT_MANAGER


class TaskService:
    @staticmethod
    @transaction.atomic
    def create(actor, title, description="", due_date=None,
               priority=Task.Priority.MEDIUM, labels=(), assignees=()):
        """Create a task owned by `actor`. Returns the saved Task.

        Raises PermissionDenied if `actor` is inactive, or asks for assignees without
        being a Project Manager. Raises ValidationError for invalid field values.
        """
        _require_active_actor(actor)
        assignees = list(assignees)
        if assignees and not can_assign(actor):
            raise PermissionDenied("Only a Project Manager can assign tasks.")

        task = Task(
            owner=actor,
            title=(title or "").strip(),
            description=description or "",
            due_date=due_date,
            priority=priority,
        )
        task.full_clean()  # blank title, bad priority, over-long title ...
        for label in labels:
            if label.is_archived:
                raise ValidationError({"labels": f"The label '{label.name}' is archived."})
        task.save()
        task.labels.set(labels)

        AuditService.record(
            actor, "task.created", task,
            details={"priority": task.priority, "status": task.status},
        )
        for user in assignees:
            TaskService.assign(task, user, actor)
        return task

    @staticmethod
    @transaction.atomic
    def assign(task, user, actor):
        """Assign `user` to `task` (Project Manager only) and notify them."""
        _require_active_actor(actor)
        if not can_assign(actor):
            raise PermissionDenied("Only a Project Manager can assign tasks.")
        if task.is_deleted:
            raise ValidationError("A deleted task cannot be assigned.")
        if not _is_active(user):
            raise ValidationError("That account is disabled and cannot be assigned tasks.")
        if TaskAssignment.objects.filter(task=task, user=user).exists():
            raise ValidationError("That user is already assigned to this task.")

        assignment = TaskAssignment.objects.create(task=task, user=user, assigned_by=actor)
        AuditService.record(
            actor, "task.assignee_added", task, details={"assignee_id": user.pk},
        )
        if user.pk != actor.pk:  # no e-mail to yourself
            event = NotificationEvent(
                kind="task.assigned",
                recipient=user,
                subject="You have been assigned a task",
                body=f"You were assigned the task '{task.title}'.",
                context={"task_id": task.pk, "assigned_by_id": actor.pk},
            )
            transaction.on_commit(lambda: NotificationService.enqueue(event))
        return assignment

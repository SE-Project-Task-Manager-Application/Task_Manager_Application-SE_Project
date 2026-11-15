"""Transactional task operations and business rules."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.services import require_task_permission
from adminpanel.services import AuditService
from notif.services import NotificationEvent, NotificationService

from .models import Task, TaskAssignment

ROLE_PROJECT_MANAGER = "project_manager"


class StaleTaskError(ValidationError):
    status_code = 409


def _is_active(user):
    return bool(user and user.is_active and not getattr(user, "deleted_at", None))


def _require_active_actor(actor):
    if not _is_active(actor):
        raise PermissionDenied("Only an active user can do this.")


def can_assign(actor):
    return _is_active(actor) and getattr(actor, "role", None) == ROLE_PROJECT_MANAGER


def _check_version(task, expected_version):
    if expected_version is None:
        return
    try:
        version = int(expected_version)
    except (TypeError, ValueError):
        raise StaleTaskError("This task was changed by someone else. Reload and try again.")
    if task.version != version:
        raise StaleTaskError("This task was changed by someone else. Reload and try again.")


class TaskService:
    @staticmethod
    @transaction.atomic
    def create(
        actor,
        title,
        description="",
        due_date=None,
        priority=Task.Priority.MEDIUM,
        labels=(),
        assignees=(),
    ):
        _require_active_actor(actor)
        labels = list(labels)
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
        task.full_clean()
        for label in labels:
            if label.is_archived:
                raise ValidationError({"labels": f"The label '{label.name}' is archived."})
        task.save()
        task.labels.set(labels)
        AuditService.record(
            actor, "task.created", task, details={"priority": task.priority, "status": task.status}
        )
        for user in assignees:
            TaskService.assign(task, user, actor)
        return task

    @staticmethod
    @transaction.atomic
    def assign(task, user, actor):
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
        AuditService.record(actor, "task.assignee_added", task, details={"assignee_id": user.pk})
        if user.pk != actor.pk:
            event = NotificationEvent(
                kind="task.assigned",
                recipient=user,
                subject="You have been assigned a task",
                body=f"You were assigned the task '{task.title}'.",
                context={"task_id": task.pk, "assigned_by_id": actor.pk},
            )
            transaction.on_commit(lambda: NotificationService.send(event))
        return assignment

    @staticmethod
    @transaction.atomic
    def update(actor, task, expected_version=None, **changes):
        _require_active_actor(actor)
        locked = Task.objects.select_for_update().get(pk=task.pk)
        require_task_permission(actor, locked, "edit")
        if locked.is_deleted:
            raise ValidationError("A deleted task cannot be edited.")
        _check_version(locked, expected_version)
        labels = changes.pop("labels", None)
        if labels is not None:
            labels = list(labels)
        assignees = changes.pop("assignees", None)
        if assignees is not None and not can_assign(actor):
            raise PermissionDenied("Only a Project Manager can reassign tasks.")
        allowed = {"title", "description", "due_date", "priority", "status"}
        invalid = set(changes) - allowed
        if invalid:
            raise ValidationError(f"Unsupported task fields: {', '.join(sorted(invalid))}.")
        before = {field: getattr(locked, field) for field in changes}
        for field, value in changes.items():
            setattr(locked, field, value.strip() if field == "title" and value else value)
        locked.version += 1
        locked.full_clean()
        if labels is not None:
            existing_label_ids = set(locked.labels.values_list("pk", flat=True))
            if any(label.is_archived and label.pk not in existing_label_ids for label in labels):
                raise ValidationError("Archived labels cannot be assigned.")
        locked.save()
        changed_fields = [
            field
            for field in ("title", "description", "due_date", "priority")
            if field in before and before[field] != getattr(locked, field)
        ]
        if labels is not None:
            if set(locked.labels.values_list("pk", flat=True)) != {label.pk for label in labels}:
                changed_fields.append("labels")
            locked.labels.set(labels)
        if assignees is not None:
            existing_assignments = {
                assignment.user_id: assignment
                for assignment in TaskAssignment.objects.filter(task=locked)
            }
            new_assignee_ids = {user.pk for user in assignees}
            removed_ids = set(existing_assignments) - new_assignee_ids
            TaskAssignment.objects.filter(task=locked, user_id__in=removed_ids).delete()
            for user_id in removed_ids:
                AuditService.record(
                    actor,
                    "task.assignee_removed",
                    locked,
                    details={"assignee_id": user_id},
                )
            for user in assignees:
                if user.pk not in existing_assignments:
                    TaskService.assign(locked, user, actor)
        # TM-F-034: the activity history shows what changed. A status change gets its own
        # event; any other edit lists the fields that changed.
        status_changed = "status" in before and before["status"] != locked.status
        if status_changed:
            AuditService.record(
                actor,
                "task.status_changed",
                locked,
                details={"from": before["status"], "to": locked.status, "version": locked.version},
            )
        if changed_fields or not status_changed:
            AuditService.record(
                actor,
                "task.updated",
                locked,
                details={"version": locked.version, "fields": changed_fields},
            )
        if locked.shares.exists():
            collaborators = {
                share.user_id: share.user
                for share in locked.shares.select_related("user")
            }
            collaborators[locked.owner_id] = locked.owner
            for collaborator in collaborators.values():
                if collaborator.pk == actor.pk:
                    continue
                event = NotificationEvent(
                    kind="task.shared_updated",
                    recipient=collaborator,
                    subject=f"Shared task updated: {locked.title}",
                    body=f"{actor.email} updated the shared task '{locked.title}'.",
                    context={"task_id": locked.pk, "updated_by_id": actor.pk},
                )
                NotificationService.enqueue_persisted(event, locked)
        return locked

    @staticmethod
    @transaction.atomic
    def delete(actor, task, expected_version=None):
        _require_active_actor(actor)
        locked = Task.objects.select_for_update().get(pk=task.pk)
        require_task_permission(actor, locked, "delete")
        if locked.is_deleted:
            raise ValidationError("Task is already deleted.")
        _check_version(locked, expected_version)
        locked.deleted_at = timezone.now()
        locked.version += 1
        locked.save(update_fields=["deleted_at", "version", "updated_at"])
        AuditService.record(actor, "task.deleted", locked)
        return locked

    @staticmethod
    @transaction.atomic
    def restore(actor, task, expected_version=None):
        _require_active_actor(actor)
        locked = Task.objects.select_for_update().get(pk=task.pk)
        require_task_permission(actor, locked, "delete")
        if not locked.is_deleted:
            raise ValidationError("Task is not deleted.")
        if locked.deleted_at < timezone.now() - timedelta(days=30):
            raise ValidationError("Tasks can only be restored within 30 days.")
        _check_version(locked, expected_version)
        locked.deleted_at = None
        locked.version += 1
        locked.save(update_fields=["deleted_at", "version", "updated_at"])
        AuditService.record(actor, "task.restored", locked)
        return locked

    @staticmethod
    @transaction.atomic
    def set_status(actor, task, status, expected_version=None):
        if status not in Task.Status.values:
            raise ValidationError("Invalid task status.")
        return TaskService.update(actor, task, expected_version=expected_version, status=status)

    @staticmethod
    def soft_delete(actor, task, expected_version=None):
        return TaskService.delete(actor, task, expected_version)

    @staticmethod
    def complete(actor, task, expected_version=None):
        return TaskService.set_status(actor, task, Task.Status.DONE, expected_version)

    @staticmethod
    def reopen(actor, task, expected_version=None):
        return TaskService.set_status(actor, task, Task.Status.TODO, expected_version)

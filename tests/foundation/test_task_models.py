"""S-04: Task, TaskAssignment and Label models (ORM level)."""

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from tasks.models import Label, Task, TaskAssignment

pytestmark = pytest.mark.django_db


def test_migrations_are_in_sync_with_models():
    # Fails if a model changed without a migration being generated.
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


def test_new_task_defaults(make_user):
    task = Task.objects.create(owner=make_user(), title="Write report")
    assert task.status == Task.Status.TODO
    assert task.priority == Task.Priority.MEDIUM
    assert task.version == 1
    assert task.deleted_at is None
    assert task.created_at and task.updated_at


def test_status_values_match_the_agreed_schema():
    assert [value for value, _ in Task.Status.choices] == ["todo", "in_progress", "done"]


def test_active_and_deleted_querysets(make_user):
    owner = make_user()
    keep = Task.objects.create(owner=owner, title="keep")
    gone = Task.objects.create(owner=owner, title="gone")
    gone.soft_delete()
    assert list(Task.objects.active()) == [keep]
    assert list(Task.objects.deleted()) == [gone]


def test_soft_delete_keeps_the_row(make_user):
    task = Task.objects.create(owner=make_user(), title="t")
    task.soft_delete()
    task.refresh_from_db()
    assert task.is_deleted
    assert Task.objects.filter(pk=task.pk).exists()


def test_task_can_have_several_assignees(make_user):
    owner, a, b = make_user("project_manager"), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="t")
    for person in (a, b):
        TaskAssignment.objects.create(task=task, user=person, assigned_by=owner)
    assert set(task.assignees.all()) == {a, b}
    assert list(a.assigned_tasks.all()) == [task]


def test_same_user_cannot_be_assigned_twice(make_user):
    owner, a = make_user("project_manager"), make_user()
    task = Task.objects.create(owner=owner, title="t")
    TaskAssignment.objects.create(task=task, user=a, assigned_by=owner)
    with pytest.raises(IntegrityError), transaction.atomic():
        TaskAssignment.objects.create(task=task, user=a, assigned_by=owner)


def test_label_names_are_unique_ignoring_case():
    Label.objects.create(name="Urgent")
    with pytest.raises(IntegrityError), transaction.atomic():
        Label.objects.create(name="urgent")


def test_labels_attach_to_tasks(make_user):
    task = Task.objects.create(owner=make_user(), title="t")
    label = Label.objects.create(name="Bug")
    task.labels.add(label)
    assert list(task.labels.all()) == [label]
    assert list(label.tasks.all()) == [task]


def test_user_with_tasks_cannot_be_hard_deleted(make_user):
    owner = make_user()
    Task.objects.create(owner=owner, title="t")
    with pytest.raises(ProtectedError):
        owner.delete()

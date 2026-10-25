"""TC-Task-01: create a task (TM-F-010), including assignment (STP 5.2).

Acceptance criterion: "Task saved and shown in the task list."
Assignment: only a Project Manager may assign; the assignee is notified.
"""

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse

from adminpanel.models import AuditRecord
from notif.services import NotificationService
from tasks.models import Label, Task, TaskAssignment
from tasks.services import TaskService

pytestmark = pytest.mark.django_db

CREATE_URL = "tasks:create"
LIST_URL = "tasks:list"


@pytest.fixture(autouse=True)
def empty_queue():
    NotificationService.clear()
    yield
    NotificationService.clear()


@pytest.fixture
def login(client, make_user):
    def _login(role="member"):
        user = make_user(role)
        client.force_login(user)
        return user

    return _login


# --- Acceptance criterion: saved and shown in the list -------------------------------

def test_created_task_is_saved_and_shown_in_the_list(client, login):
    user = login()
    response = client.post(
        reverse(CREATE_URL),
        {"title": "Write report", "description": "Q3 numbers", "priority": "high",
         "due_date": "2026-10-30T17:00"},
        follow=True,
    )
    assert response.redirect_chain[-1][0] == reverse(LIST_URL)
    task = Task.objects.get()
    assert (task.title, task.description, task.priority) == ("Write report", "Q3 numbers", "high")
    assert task.owner == user and task.status == "todo"
    assert task.due_date.year == 2026 and task.due_date.month == 10
    assert "Write report" in response.content.decode()
    assert "Task created." in response.content.decode()


def test_only_title_is_required(client, login):
    login()
    client.post(reverse(CREATE_URL), {"title": "Just a title", "priority": "medium"})
    task = Task.objects.get()
    assert task.description == "" and task.due_date is None


def test_blank_title_is_rejected_with_a_message(client, login):
    login()
    response = client.post(reverse(CREATE_URL), {"title": "   ", "priority": "medium"})
    assert response.status_code == 200
    assert Task.objects.count() == 0
    html = response.content.decode()
    assert "This field is required." in html
    assert 'role="alert"' in html


def test_invalid_priority_is_rejected(client, login):
    login()
    response = client.post(reverse(CREATE_URL), {"title": "x", "priority": "urgent!!"})
    assert response.status_code == 200 and Task.objects.count() == 0


def test_creating_a_task_writes_an_audit_record(client, login):
    user = login()
    client.post(reverse(CREATE_URL), {"title": "Audited", "priority": "low"})
    task = Task.objects.get()
    record = AuditRecord.objects.get(action="task.created")
    assert (record.actor, record.target_type, record.target_id) == (user, "task", str(task.pk))


def test_labels_can_be_attached_but_archived_ones_are_not_offered(client, login):
    login()
    live = Label.objects.create(name="Bug")
    old = Label.objects.create(name="Old", is_archived=True)
    page = client.get(reverse(CREATE_URL)).content.decode()
    assert "Bug" in page and "Old" not in page
    client.post(reverse(CREATE_URL), {"title": "x", "priority": "low", "labels": [live.pk]})
    assert list(Task.objects.get().labels.all()) == [live]
    with pytest.raises(ValidationError):
        TaskService.create(Task.objects.get().owner, "y", labels=[old])


def test_list_shows_only_own_and_assigned_tasks(client, login, make_user):
    me = login()
    other = make_user()
    Task.objects.create(owner=me, title="mine")
    Task.objects.create(owner=other, title="theirs")
    assigned = Task.objects.create(owner=other, title="given to me")
    TaskAssignment.objects.create(task=assigned, user=me, assigned_by=other)
    deleted = Task.objects.create(owner=me, title="removed")
    deleted.soft_delete()
    html = client.get(reverse(LIST_URL)).content.decode()
    assert "mine" in html and "given to me" in html
    assert "theirs" not in html and "removed" not in html


def test_anonymous_user_is_sent_to_login(client):
    for name in (CREATE_URL, LIST_URL):
        response = client.get(reverse(name))
        assert response.status_code == 302
        assert response["Location"].startswith("/accounts/login/?next=")


# --- Assignment (STP 5.2): Project Manager only, assignee notified -------------------

def test_project_manager_can_assign_while_creating(client, login, make_user):
    pm = login("project_manager")
    worker = make_user()
    client.post(reverse(CREATE_URL),
                {"title": "Delegated", "priority": "medium", "assignees": [worker.pk]})
    task = Task.objects.get()
    assignment = TaskAssignment.objects.get()
    assert (assignment.task, assignment.user, assignment.assigned_by) == (task, worker, pm)
    assert AuditRecord.objects.filter(action="task.assignee_added").count() == 1


def test_assignee_is_emailed_after_commit(make_user, django_capture_on_commit_callbacks):
    pm, worker = make_user("project_manager"), make_user()
    with django_capture_on_commit_callbacks(execute=True):
        TaskService.create(pm, "Delegated", assignees=[worker])
    assert [m.to for m in mail.outbox] == [[worker.email]]
    assert mail.outbox[0].subject == "You have been assigned a task"
    assert "Delegated" in mail.outbox[0].body


def test_no_email_if_the_transaction_never_commits(make_user):
    pm, worker = make_user("project_manager"), make_user()
    TaskService.create(pm, "Delegated", assignees=[worker])  # on_commit callbacks not run
    assert mail.outbox == []


def test_assigning_to_yourself_sends_no_email(make_user, django_capture_on_commit_callbacks):
    pm = make_user("project_manager")
    with django_capture_on_commit_callbacks(execute=True):
        TaskService.create(pm, "Mine", assignees=[pm])
    assert mail.outbox == []


def test_mail_failure_does_not_break_assignment(
    make_user, monkeypatch, django_capture_on_commit_callbacks
):
    def boom(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr("notif.services.send_mail", boom)
    pm, worker = make_user("project_manager"), make_user()
    with django_capture_on_commit_callbacks(execute=True):
        task = TaskService.create(pm, "Delegated", assignees=[worker])
    assert TaskAssignment.objects.filter(task=task, user=worker).exists()


def test_mail_connections_time_out(settings):
    assert settings.EMAIL_TIMEOUT and settings.EMAIL_TIMEOUT <= 10


def test_member_does_not_get_an_assignee_field(client, login):
    login("member")
    assert "assignees" not in client.get(reverse(CREATE_URL)).content.decode()


def test_project_manager_gets_an_assignee_field(client, login, make_user):
    login("project_manager")
    make_user(email="worker@example.com")
    page = client.get(reverse(CREATE_URL)).content.decode()
    assert "assignees" in page and "worker@example.com" in page


def test_forged_assignees_from_a_member_are_ignored(client, login, make_user):
    login("member")
    worker = make_user()
    client.post(reverse(CREATE_URL),
                {"title": "Sneaky", "priority": "low", "assignees": [worker.pk]})
    assert Task.objects.count() == 1
    assert TaskAssignment.objects.count() == 0


def test_service_refuses_assignment_by_non_project_manager(make_user):
    member, worker = make_user("member"), make_user()
    with pytest.raises(PermissionDenied):
        TaskService.create(member, "x", assignees=[worker])
    assert Task.objects.count() == 0  # the whole create rolled back
    for role in ("member", "admin"):  # SAD 4.3: Project Manager only
        task = Task.objects.create(owner=make_user(), title="t")
        with pytest.raises(PermissionDenied):
            TaskService.assign(task, worker, make_user(role))


def test_cannot_assign_a_disabled_account_twice_or_on_a_deleted_task(make_user):
    pm, worker, gone = make_user("project_manager"), make_user(), make_user()
    gone.is_active = False
    gone.save()
    task = Task.objects.create(owner=pm, title="t")
    with pytest.raises(ValidationError):
        TaskService.assign(task, gone, pm)
    TaskService.assign(task, worker, pm)
    with pytest.raises(ValidationError):
        TaskService.assign(task, worker, pm)
    task.soft_delete()
    with pytest.raises(ValidationError):
        TaskService.assign(task, make_user(), pm)


def test_inactive_user_cannot_create(make_user):
    user = make_user()
    user.is_active = False
    with pytest.raises(PermissionDenied):
        TaskService.create(user, "x")

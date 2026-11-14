"""TC-Collab-05 (TM-F-034): chronological activity history for each task.

Acceptance: the activity log displays events in the correct order with timestamps.
Design (SAD): events (status changes, edits, comments, assignments) are written through
AuditService, with timestamps stored in UTC.
"""

from datetime import UTC

import pytest
from django.urls import reverse

from adminpanel.models import AuditRecord
from adminpanel.services import AuditService
from collab.models import TaskShare
from collab.services import ActivityService, CommentService, TaskShareService
from tasks.models import Task
from tasks.services import TaskService

pytestmark = pytest.mark.django_db


@pytest.fixture
def team(make_user):
    pm = make_user(role="project_manager", email="pm@example.com")
    member = make_user(email="member@example.com")
    stranger = make_user(email="stranger@example.com")
    return pm, member, stranger


def _url(task):
    return reverse("collab:task_activity", args=[task.pk])


def _actions(actor, task):
    return [entry.action for entry in ActivityService.for_task(actor, task)]


def test_history_lists_every_event_in_order(team):
    pm, member, _ = team
    task = TaskService.create(pm, title="Plan sprint", assignees=[member])
    TaskService.update(pm, task, title="Plan sprint 3", priority=Task.Priority.HIGH)
    TaskService.set_status(member, task, Task.Status.IN_PROGRESS)
    CommentService.add(member, task, "Started on the backlog.")
    TaskShareService.share(task, member, TaskShare.Permission.VIEWER, pm)
    TaskService.set_status(member, task, Task.Status.DONE)
    TaskService.delete(pm, task)
    TaskService.restore(pm, task)

    entries = ActivityService.for_task(pm, task)

    assert [entry.action for entry in entries] == [
        "task.created",
        "task.assignee_added",
        "task.updated",
        "task.status_changed",
        "task.commented",
        "task.shared",
        "task.status_changed",
        "task.deleted",
        "task.restored",
    ]
    assert [entry.description for entry in entries] == [
        "created the task",
        "assigned member@example.com",
        "edited the title, priority",
        "changed the status from To do to In progress",
        "commented: “Started on the backlog.”",
        "shared the task with member@example.com as Viewer",
        "changed the status from In progress to Done",
        "deleted the task",
        "restored the task",
    ]
    assert entries[0].actor == "pm@example.com"
    assert entries[3].actor == "member@example.com"
    timestamps = [entry.timestamp for entry in entries]
    assert timestamps == sorted(timestamps)


def test_timestamps_are_stored_in_utc(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="UTC check")
    TaskService.set_status(pm, task, Task.Status.DONE)
    for entry in ActivityService.for_task(pm, task):
        assert entry.timestamp.utcoffset().total_seconds() == 0
    record = AuditRecord.objects.filter(action="task.status_changed").get()
    assert record.created_at.astimezone(UTC) == record.created_at
    assert record.details == {"from": "todo", "to": "done", "version": 2}


def test_status_only_change_records_one_status_event(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Status only")
    TaskService.set_status(pm, task, Task.Status.DONE)
    assert _actions(pm, task) == ["task.created", "task.status_changed"]


def test_edit_with_status_and_fields_records_both(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Both")
    TaskService.update(pm, task, description="More detail", status=Task.Status.IN_PROGRESS)
    assert _actions(pm, task) == ["task.created", "task.status_changed", "task.updated"]
    edit = AuditRecord.objects.get(action="task.updated")
    assert edit.details == {"version": 2, "fields": ["description"]}


def test_save_without_changes_is_still_recorded(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Unchanged")
    TaskService.update(pm, task, title="Unchanged", status=Task.Status.TODO)
    entries = ActivityService.for_task(pm, task)
    assert [entry.action for entry in entries] == ["task.created", "task.updated"]
    assert entries[-1].description == "edited the task"


def test_assignment_removal_and_share_changes_are_described(team, make_user):
    pm, member, _ = team
    other = make_user(email="other@example.com")
    task = TaskService.create(pm, title="People", assignees=[member])
    TaskService.update(pm, task, assignees=[other])
    TaskShareService.share(task, member, TaskShare.Permission.VIEWER, pm)
    TaskShareService.share(task, member, TaskShare.Permission.EDITOR, pm)
    TaskShareService.revoke(task, member, pm)

    descriptions = [entry.description for entry in ActivityService.for_task(pm, task)]

    assert "unassigned member@example.com" in descriptions
    assert "assigned other@example.com" in descriptions
    assert descriptions[-3:] == [
        "shared the task with member@example.com as Viewer",
        "changed member@example.com's access to Editor",
        "removed member@example.com's access",
    ]


def test_attachment_and_unknown_events_are_described(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Files")
    AuditService.record(pm, "task.attachment_added", task, details={"filename": "spec.pdf"})
    AuditService.record(pm, "task.some_future_event", task)
    descriptions = [entry.description for entry in ActivityService.for_task(pm, task)]
    assert descriptions[-2:] == ["attached spec.pdf", "some future event"]


def test_long_comment_is_shortened(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Long comment")
    CommentService.add(pm, task, "word " * 50)
    description = ActivityService.for_task(pm, task)[-1].description
    assert description.startswith("commented: “word word")
    assert description.endswith("…”")
    assert len(description) < 100


def test_other_tasks_events_are_not_included(team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Mine")
    other = TaskService.create(pm, title="Other")
    TaskService.set_status(pm, other, Task.Status.DONE)
    assert _actions(pm, task) == ["task.created"]


def test_page_shows_events_in_order_with_timestamps(client, team):
    pm, member, _ = team
    task = TaskService.create(pm, title="Page check", assignees=[member])
    CommentService.add(member, task, "First comment")
    TaskService.set_status(member, task, Task.Status.DONE)
    client.force_login(member)

    response = client.get(_url(task))

    assert response.status_code == 200
    html = response.content.decode()
    order = [
        html.index("created the task"),
        html.index("assigned member@example.com"),
        html.index("commented: “First comment”"),
        html.index("changed the status from To do to Done"),
    ]
    assert order == sorted(order)
    for entry in ActivityService.for_task(member, task):
        assert entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") + " UTC" in html
        assert f'datetime="{entry.timestamp.isoformat()}"' in html


def test_edit_through_the_form_shows_in_history(client, team):
    _, member, _ = team
    task = TaskService.create(member, title="Form edit")
    client.force_login(member)
    response = client.post(
        reverse("tasks:edit", args=[task.pk]),
        {
            "title": "Form edit v2",
            "description": "",
            "priority": "high",
            "status": "in_progress",
            "expected_version": task.version,
        },
    )
    assert response.status_code == 302
    html = client.get(_url(task)).content.decode()
    assert "changed the status from To do to In progress" in html
    assert "edited the title, priority" in html


@pytest.mark.parametrize("permission", ["viewer", "editor"])
def test_shared_users_can_see_history(client, team, permission):
    pm, member, _ = team
    task = TaskService.create(pm, title="Shared")
    TaskShareService.share(task, member, permission, pm)
    client.force_login(member)
    assert client.get(_url(task)).status_code == 200


def test_user_without_access_gets_403(client, team):
    pm, member, stranger = team
    task = TaskService.create(pm, title="Private")
    TaskShareService.share(task, member, TaskShare.Permission.VIEWER, pm)
    TaskShareService.revoke(task, member, pm)
    for user in (stranger, member):
        client.force_login(user)
        response = client.get(_url(task))
        assert response.status_code == 403
        assert "Private" not in response.content.decode()


def test_anonymous_user_is_sent_to_login(client, team):
    task = TaskService.create(team[0], title="Login first")
    response = client.get(_url(task))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]


def test_missing_task_gives_404(client, team):
    client.force_login(team[0])
    assert client.get(reverse("collab:task_activity", args=[999999])).status_code == 404


def test_deleted_task_history_is_still_visible_to_owner(client, team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Gone")
    TaskService.delete(pm, task)
    client.force_login(pm)
    html = client.get(_url(task)).content.decode()
    assert "This task is deleted." in html
    assert "deleted the task" in html


def test_comment_text_is_escaped_in_history(client, team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Escape")
    CommentService.add(pm, task, "<script>alert('x')</script>")
    client.force_login(pm)
    html = client.get(_url(task)).content.decode()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_task_list_and_comments_page_link_to_history(client, team):
    pm, _, _ = team
    task = TaskService.create(pm, title="Linked")
    client.force_login(pm)
    assert _url(task) in client.get(reverse("tasks:list")).content.decode()
    comments_url = reverse("collab:task_comments", args=[task.pk])
    assert _url(task) in client.get(comments_url).content.decode()

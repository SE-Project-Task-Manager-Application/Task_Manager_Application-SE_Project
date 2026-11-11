"""TC-Collab-04 (TM-F-033): a user can comment on a task they have access to.

Acceptance: the comment is saved with author and timestamp and is visible to everyone
with access to the task. Design note (SAD): comments feed the task activity history
(TM-F-034) through a `task.commented` audit record.
"""

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import AuditRecord
from collab.models import COMMENT_MAX_LENGTH, Comment
from collab.services import CommentService
from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db


@pytest.fixture
def people(make_user):
    owner, assignee, stranger = make_user(), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Write report")
    TaskAssignment.objects.create(task=task, user=assignee, assigned_by=owner)
    return task, owner, assignee, stranger


def _url(task):
    return reverse("collab:task_comments", args=[task.pk])


def test_owner_comment_is_saved_with_author_and_timestamp(client, people):
    task, owner, _, _ = people
    client.force_login(owner)
    before = timezone.now()

    response = client.post(_url(task), {"body": "  First draft is ready.  "})

    assert response.status_code == 302
    assert response["Location"] == _url(task)
    comment = Comment.objects.get(task=task)
    assert comment.author == owner
    assert comment.body == "First draft is ready."
    assert before <= comment.created_at <= timezone.now()


def test_comment_is_visible_to_everyone_with_access(client, people):
    task, owner, assignee, _ = people
    comment = CommentService.add(owner, task, "Please review section 2.")

    for viewer in (owner, assignee):
        client.force_login(viewer)
        page = client.get(_url(task))
        assert page.status_code == 200
        html = page.content.decode()
        assert "Please review section 2." in html
        assert owner.email in html
        assert comment.created_at.strftime("%Y-%m-%d %H:%M") in html


def test_assignee_can_comment_and_owner_sees_it(client, people):
    task, owner, assignee, _ = people
    client.force_login(assignee)
    response = client.post(_url(task), {"body": "Section 2 reviewed."}, follow=True)
    assert response.status_code == 200
    assert "Comment added." in response.content.decode()

    client.force_login(owner)
    html = client.get(_url(task)).content.decode()
    assert "Section 2 reviewed." in html and assignee.email in html


def test_user_without_access_cannot_read_or_add_comments(client, people):
    task, owner, _, stranger = people
    CommentService.add(owner, task, "Private note")
    client.force_login(stranger)

    page = client.get(_url(task))
    assert page.status_code == 403
    assert "Private note" not in page.content.decode()

    response = client.post(_url(task), {"body": "Let me in"})
    assert response.status_code == 403
    assert not Comment.objects.filter(author=stranger).exists()
    with pytest.raises(PermissionDenied):
        CommentService.add(stranger, task, "Let me in")


def test_anonymous_user_is_sent_to_login(client, people):
    task = people[0]
    response = client.post(_url(task), {"body": "Hello"})
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]
    assert not Comment.objects.exists()


def test_disabled_user_cannot_comment(people):
    task, owner, _, _ = people
    owner.is_active = False
    owner.save(update_fields=["is_active"])
    with pytest.raises(PermissionDenied):
        CommentService.add(owner, task, "Still here?")


@pytest.mark.parametrize("body", ["", "    ", "x" * (COMMENT_MAX_LENGTH + 1)])
def test_blank_or_too_long_comment_is_rejected(client, people, body):
    task, owner, _, _ = people
    client.force_login(owner)
    response = client.post(_url(task), {"body": body})
    assert response.status_code == 400
    assert not Comment.objects.exists()
    with pytest.raises(ValidationError):
        CommentService.add(owner, task, body)


def test_deleted_task_cannot_be_commented_on(client, people):
    task, owner, _, _ = people
    task.soft_delete()
    client.force_login(owner)
    assert client.get(_url(task)).status_code == 404
    assert client.post(_url(task), {"body": "Hello"}).status_code == 404
    with pytest.raises(ValidationError):
        CommentService.add(owner, task, "Hello")
    assert not Comment.objects.exists()


def test_comments_are_listed_oldest_first(client, people):
    task, owner, assignee, _ = people
    CommentService.add(owner, task, "Comment one")
    CommentService.add(assignee, task, "Comment two")
    CommentService.add(owner, task, "Comment three")
    client.force_login(owner)
    html = client.get(_url(task)).content.decode()
    assert html.index("Comment one") < html.index("Comment two") < html.index("Comment three")


def test_comment_writes_activity_record(people):
    task, _, assignee, _ = people
    comment = CommentService.add(assignee, task, "Done with my part.")
    record = AuditRecord.objects.get(action="task.commented")
    assert record.actor == assignee
    assert (record.target_type, record.target_id) == ("task", str(task.pk))
    assert record.details == {"comment_id": comment.pk}
    assert record.created_at == comment.created_at


def test_comment_text_is_escaped(client, people):
    task, owner, _, _ = people
    CommentService.add(owner, task, "<script>alert('x')</script>")
    client.force_login(owner)
    html = client.get(_url(task)).content.decode()
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_posting_a_comment_requires_csrf_token(people):
    task, owner, _, _ = people
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(owner)
    response = csrf_client.post(_url(task), {"body": "No token"})
    assert response.status_code == 403
    assert not Comment.objects.exists()


def test_task_list_links_to_comments(client, people):
    task, owner, _, _ = people
    client.force_login(owner)
    html = client.get(reverse("tasks:list")).content.decode()
    assert _url(task) in html

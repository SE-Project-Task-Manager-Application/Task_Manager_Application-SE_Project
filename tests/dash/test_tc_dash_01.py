"""TC-Dash-01: dashboard summary counts match the underlying data (TM-F-040).

Acceptance criterion: "Dashboard counts match underlying data."
"""

import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db

DASH_URL = "dash:index"


@pytest.fixture
def login(client, make_user):
    def _login(role="member"):
        user = make_user(role)
        client.force_login(user)
        return user

    return _login


def make_task(owner, title, status=Task.Status.TODO, due_delta_days=None):
    due = None
    if due_delta_days is not None:
        due = timezone.now() + datetime.timedelta(days=due_delta_days)
    return Task.objects.create(owner=owner, title=title, status=status, due_date=due)


@pytest.fixture
def owned_tasks(login):
    """A known mix: 2 open, 1 of them overdue, plus 1 completed and 1 deleted."""
    user = login()
    make_task(user, "open no due date")
    make_task(user, "open overdue", due_delta_days=-2)
    make_task(user, "open future", due_delta_days=3)
    make_task(user, "done", status=Task.Status.DONE, due_delta_days=-1)
    deleted = make_task(user, "deleted", due_delta_days=1)
    deleted.soft_delete()
    return user


def test_counts_match_underlying_data(client, owned_tasks):
    response = client.get(reverse(DASH_URL))
    assert response.status_code == 200
    counts = response.context["counts"]
    # open: "open no due date", "open overdue", "open future" (deleted and done excluded)
    assert counts["open"] == 3
    # overdue: only "open overdue" (past due, not done)
    assert counts["overdue"] == 1
    assert counts["completed"] == 1
    assert counts["total"] == 4  # soft-deleted task excluded


def test_counts_rendered_on_page(client, owned_tasks):
    content = client.get(reverse(DASH_URL)).content.decode()
    assert "Open" in content and "Overdue" in content and "Completed" in content


def test_range_filters_by_due_date(client, owned_tasks):
    """A chosen range keeps only tasks due inside it; tasks without a due date drop out."""
    today = timezone.localdate()
    response = client.get(
        reverse(DASH_URL),
        {"start": (today - datetime.timedelta(days=7)).isoformat(), "end": today.isoformat()},
    )
    counts = response.context["counts"]
    # In range: "open overdue" (due 2 days ago) and "done" (due yesterday).
    assert counts["open"] == 1
    assert counts["overdue"] == 1
    assert counts["completed"] == 1
    assert counts["total"] == 2


def test_swapped_range_is_normalised(client, owned_tasks):
    today = timezone.localdate()
    response = client.get(
        reverse(DASH_URL),
        {"start": today.isoformat(), "end": (today - datetime.timedelta(days=7)).isoformat()},
    )
    assert response.status_code == 200
    assert response.context["counts"]["total"] == 2


def test_invalid_range_values_are_ignored(client, owned_tasks):
    response = client.get(reverse(DASH_URL), {"start": "not-a-date", "end": "2026-13-99"})
    assert response.status_code == 200
    assert response.context["counts"]["total"] == 4


def test_other_users_tasks_are_not_counted(client, login, make_user):
    login()
    other = make_user(email="other@example.com")
    make_task(other, "someone else's task", due_delta_days=-1)
    response = client.get(reverse(DASH_URL))
    assert response.context["counts"]["total"] == 0


def test_assigned_tasks_are_counted(client, login, make_user):
    user = login()
    manager = make_user(role="project_manager", email="pm@example.com")
    task = make_task(manager, "assigned task", due_delta_days=1)
    TaskAssignment.objects.create(task=task, user=user, assigned_by=manager)
    response = client.get(reverse(DASH_URL))
    assert response.context["counts"]["open"] == 1


def test_login_required(client):
    response = client.get(reverse(DASH_URL))
    assert response.status_code == 302
    assert "/accounts/login" in response["Location"]

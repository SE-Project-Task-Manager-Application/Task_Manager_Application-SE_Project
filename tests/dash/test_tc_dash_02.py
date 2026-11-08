"""TC-Dash-02: exported CSV opens correctly and matches on-screen totals (TM-F-041).

Acceptance criterion: "Downloaded CSV opens correctly and matches on-screen totals."
The CSV is built from the same query as the dashboard (SAD 4.5).
"""

import csv
import datetime
import io

import pytest
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task

pytestmark = pytest.mark.django_db

DASH_URL = "dash:index"
CSV_URL = "dash:export_csv"


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
    user = login()
    make_task(user, "open no due date")
    make_task(user, "open overdue", due_delta_days=-2)
    make_task(user, "open future", due_delta_days=3)
    make_task(user, "done", status=Task.Status.DONE, due_delta_days=-1)
    return user


def read_csv(response):
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert "attachment" in response["Content-Disposition"]
    return list(csv.reader(io.StringIO(response.content.decode())))


def summary_block(rows):
    """The summary rows at the bottom of the export, as {name: count}."""
    start = rows.index(["Summary", "Count"])
    return {name: int(count) for name, count in rows[start + 1 :]}


def test_csv_is_an_attachment_and_parses(client, owned_tasks):
    rows = read_csv(client.get(reverse(CSV_URL)))
    assert rows[0] == ["title", "status", "priority", "due_date", "owner", "assignees", "labels"]


def task_titles(rows):
    """Titles from the task rows: everything between the header and the blank line."""
    body = rows[1 : rows.index([])]
    return [row[0] for row in body]


def test_csv_lists_the_same_tasks(client, owned_tasks):
    rows = read_csv(client.get(reverse(CSV_URL)))
    assert sorted(task_titles(rows)) == ["done", "open future", "open no due date", "open overdue"]


def test_csv_totals_match_on_screen_totals(client, owned_tasks):
    on_screen = client.get(reverse(DASH_URL)).context["counts"]
    summary = summary_block(read_csv(client.get(reverse(CSV_URL))))
    assert summary["Open"] == on_screen["open"]
    assert summary["Overdue"] == on_screen["overdue"]
    assert summary["Completed"] == on_screen["completed"]
    assert summary["Total"] == on_screen["total"]


def test_csv_honours_the_chosen_range(client, owned_tasks):
    today = timezone.localdate()
    params = {
        "start": (today - datetime.timedelta(days=7)).isoformat(),
        "end": today.isoformat(),
    }
    rows = read_csv(client.get(reverse(CSV_URL), params))
    on_screen = client.get(reverse(DASH_URL), params).context["counts"]
    summary = summary_block(rows)
    assert summary["Total"] == 2
    assert summary["Total"] == on_screen["total"]
    assert sorted(task_titles(rows)) == ["done", "open overdue"]


def test_csv_only_contains_the_users_own_tasks(client, login, make_user):
    login()
    other = make_user(email="other@example.com")
    make_task(other, "someone else's task")
    rows = read_csv(client.get(reverse(CSV_URL)))
    assert summary_block(rows)["Total"] == 0


def test_login_required(client):
    response = client.get(reverse(CSV_URL))
    assert response.status_code == 302

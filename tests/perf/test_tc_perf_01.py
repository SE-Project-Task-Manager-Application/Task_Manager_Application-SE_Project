"""TC-Perf-01 (TM-NF-001): create, edit and view tasks respond within 2 seconds.

This is the automated guard that runs in GitHub Actions on every PR. It times each
action end to end through Django (URL routing, middleware, auth, ORM, templates)
against a user who already has a realistic number of tasks. The formal measurement
over HTTP, with several simulated users, is the Locust run in perf/ (see perf/README.md).
"""

import re
import time

import pytest
from django.urls import reverse

from tasks.models import Label, Task, TaskAssignment

pytestmark = pytest.mark.django_db

LIMIT_SECONDS = 2.0  # TM-NF-001
EXISTING_TASKS = 300  # tasks the user already has, so the list and filters do real work
ROUNDS = 5  # each action is timed this many times; the slowest round must pass


@pytest.fixture
def busy_user(make_user):
    """A member with many tasks (some labelled, some assigned to them) plus a PM's tasks."""
    user = make_user()
    pm = make_user(role="project_manager")
    labels = [Label.objects.create(name=f"Perf label {i}") for i in range(5)]
    statuses = list(Task.Status.values)
    priorities = list(Task.Priority.values)
    tasks = Task.objects.bulk_create(
        Task(
            owner=user,
            title=f"Existing task {i}",
            description="Seeded for TC-Perf-01.",
            status=statuses[i % len(statuses)],
            priority=priorities[i % len(priorities)],
        )
        for i in range(EXISTING_TASKS)
    )
    for i, task in enumerate(tasks[:100]):
        task.labels.add(labels[i % len(labels)])
    pm_tasks = Task.objects.bulk_create(
        Task(owner=pm, title=f"PM task {i}") for i in range(50)
    )
    TaskAssignment.objects.bulk_create(
        TaskAssignment(task=task, user=user, assigned_by=pm) for task in pm_tasks
    )
    return user


def _timed(action):
    start = time.perf_counter()
    response = action()
    return response, time.perf_counter() - start


def _slowest(action, check):
    slowest = 0.0
    for _ in range(ROUNDS):
        response, elapsed = _timed(action)
        check(response)
        slowest = max(slowest, elapsed)
    return slowest


def test_view_task_list_within_2_seconds(client, busy_user):
    client.force_login(busy_user)
    url = reverse("tasks:list")

    def check(response):
        assert response.status_code == 200

    slowest = _slowest(lambda: client.get(url), check)
    assert slowest < LIMIT_SECONDS, f"Task list took {slowest:.3f}s"


def test_view_filtered_task_list_within_2_seconds(client, busy_user):
    client.force_login(busy_user)
    url = reverse("tasks:list")
    params = {"q": "task 1", "status": "todo", "priority": "high", "sort": "due_date"}

    def check(response):
        assert response.status_code == 200

    slowest = _slowest(lambda: client.get(url, params), check)
    assert slowest < LIMIT_SECONDS, f"Filtered task list took {slowest:.3f}s"


def test_create_task_within_2_seconds(client, busy_user):
    client.force_login(busy_user)
    url = reverse("tasks:create")
    before = Task.objects.count()

    def check(response):
        assert response.status_code == 302

    slowest = _slowest(
        lambda: client.post(url, {"title": "Perf create", "priority": "medium"}), check
    )
    assert Task.objects.count() == before + ROUNDS
    assert slowest < LIMIT_SECONDS, f"Create task took {slowest:.3f}s"


def test_open_edit_form_within_2_seconds(client, busy_user):
    client.force_login(busy_user)
    task = Task.objects.filter(owner=busy_user).first()
    url = reverse("tasks:edit", args=[task.pk])

    def check(response):
        assert response.status_code == 200

    slowest = _slowest(lambda: client.get(url), check)
    assert slowest < LIMIT_SECONDS, f"Edit form took {slowest:.3f}s"


def test_save_task_edit_within_2_seconds(client, busy_user):
    client.force_login(busy_user)
    task = Task.objects.filter(owner=busy_user).first()
    url = reverse("tasks:edit", args=[task.pk])
    slowest = 0.0
    for round_number in range(ROUNDS):
        page = client.get(url).content.decode()
        version = re.search(r'name="expected_version"[^>]*value="(\d+)"', page).group(1)
        data = {
            "title": f"Edited {round_number}",
            "description": "",
            "priority": "high",
            "status": "in_progress",
            "expected_version": version,
        }
        response, elapsed = _timed(lambda data=data: client.post(url, data))
        assert response.status_code == 302, response.content.decode()[:500]
        slowest = max(slowest, elapsed)
    task.refresh_from_db()
    assert task.title == f"Edited {ROUNDS - 1}"
    assert slowest < LIMIT_SECONDS, f"Save edit took {slowest:.3f}s"

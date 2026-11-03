"""TC-Org-01: assign labels to a task (TM-F-020).

Acceptance criterion: "Labels persist and display as chips."
Design note (SAD): archived labels are hidden at task creation.
"""

import pytest
from django.urls import reverse

from tasks.models import Label, Task

pytestmark = pytest.mark.django_db

CREATE_URL = "tasks:create"
LIST_URL = "tasks:list"


@pytest.fixture
def user(client, make_user):
    person = make_user()
    client.force_login(person)
    return person


def test_assigned_labels_persist_and_display_as_chips(client, user):
    bug = Label.objects.create(name="Bug")
    urgent = Label.objects.create(name="Urgent")
    response = client.post(
        reverse(CREATE_URL),
        {"title": "Fix login", "priority": "high", "labels": [bug.pk, urgent.pk]},
        follow=True,
    )
    assert set(Task.objects.get().labels.all()) == {bug, urgent}
    html = response.content.decode()
    assert '<span class="chip">Bug</span>' in html
    assert '<span class="chip">Urgent</span>' in html


def test_labels_are_still_there_when_the_list_is_reloaded(client, user):
    label = Label.objects.create(name="Bug")
    client.post(reverse(CREATE_URL), {"title": "x", "priority": "low", "labels": [label.pk]})
    html = client.get(reverse(LIST_URL)).content.decode()
    assert '<span class="chip">Bug</span>' in html


def test_a_task_without_labels_shows_no_chip(client, user):
    client.post(reverse(CREATE_URL), {"title": "Plain", "priority": "low"})
    assert Task.objects.count() == 1
    html = client.get(reverse(LIST_URL)).content.decode()
    assert 'class="chip"' not in html


def test_archived_label_is_not_offered_when_creating_a_task(client, user):
    Label.objects.create(name="Visible-label")
    Label.objects.create(name="Archived-label", is_archived=True)
    page = client.get(reverse(CREATE_URL)).content.decode()
    assert "Visible-label" in page
    assert "Archived-label" not in page


def test_posting_an_archived_label_is_rejected(client, user):
    old = Label.objects.create(name="Archived-label", is_archived=True)
    response = client.post(
        reverse(CREATE_URL), {"title": "x", "priority": "low", "labels": [old.pk]}
    )
    assert response.status_code == 200
    assert Task.objects.count() == 0


def test_label_archived_later_is_still_shown_on_the_existing_task(client, user):
    label = Label.objects.create(name="Bug")
    task = Task.objects.create(owner=user, title="Existing")
    task.labels.add(label)
    label.is_archived = True
    label.save()
    html = client.get(reverse(LIST_URL)).content.decode()
    assert '<span class="chip">Bug</span>' in html

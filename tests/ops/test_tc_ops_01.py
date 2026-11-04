"""TC-Ops-01: stability and error handling (TM-NF-002, SRS 5).

Acceptance criterion: no crashes during the test scenarios. Bad input to the
create-task form, an SMTP outage while the assignment e-mail is sent, and
requests for pages that do not exist must all fail gracefully (form error,
normal redirect, or 404) - never a 500.
"""

import pytest
from django.urls import reverse

from tasks.models import Label, Task, TaskAssignment

pytestmark = pytest.mark.django_db

CREATE_URL = "tasks:create"
LIST_URL = "tasks:list"


@pytest.fixture
def login(client, make_user):
    def _login(role="member"):
        user = make_user(role)
        client.force_login(user)
        return user

    return _login


# --- Bad input: the form reports an error instead of crashing ------------------------

def _post_create(client, **overrides):
    data = {"title": "A task", "priority": "medium"}
    data.update(overrides)
    return client.post(reverse(CREATE_URL), data)


def test_blank_title_shows_an_error_not_a_crash(client, login):
    login()
    response = _post_create(client, title="")
    assert response.status_code == 200
    assert Task.objects.count() == 0


def test_overlong_title_shows_an_error_not_a_crash(client, login):
    login()
    response = _post_create(client, title="x" * 201)
    assert response.status_code == 200
    assert Task.objects.count() == 0


def test_invalid_priority_shows_an_error_not_a_crash(client, login):
    login()
    response = _post_create(client, priority="urgent")
    assert response.status_code == 200
    assert Task.objects.count() == 0


def test_malformed_due_date_shows_an_error_not_a_crash(client, login):
    login()
    response = _post_create(client, due_date="not-a-date")
    assert response.status_code == 200
    assert Task.objects.count() == 0


def test_forged_assignees_from_a_member_do_not_crash_or_assign(client, login, make_user):
    login("member")
    worker = make_user()
    response = _post_create(client, assignees=[worker.pk])
    assert response.status_code == 302  # task created, forged field ignored
    assert Task.objects.count() == 1
    assert TaskAssignment.objects.count() == 0


def test_archived_label_is_rejected_without_a_crash(client, login):
    login()
    archived = Label.objects.create(name="Old", is_archived=True)
    response = _post_create(client, labels=[archived.pk])
    assert response.status_code == 200
    assert Task.objects.count() == 0


# --- SMTP outage: the request still succeeds when the mail server is down ------------

@pytest.mark.django_db(transaction=True)
def test_smtp_outage_does_not_break_task_creation(client, login, make_user, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("mail server unreachable")

    monkeypatch.setattr("notif.services.send_mail", boom)
    login("project_manager")
    worker = make_user()
    response = _post_create(client, assignees=[worker.pk])
    assert response.status_code == 302
    assert response["Location"] == reverse(LIST_URL)
    task = Task.objects.get()
    assert TaskAssignment.objects.filter(task=task, user=worker).exists()


# --- Missing pages: a graceful 404, not a crash ---------------------------------------

def test_unknown_task_url_returns_404(client, login):
    login()
    assert client.get("/tasks/999/").status_code == 404


def test_unknown_site_url_returns_404(client, login):
    login()
    assert client.get("/no-such-page/").status_code == 404


# --- Normal use: the built pages load --------------------------------------------------

def test_built_pages_load_for_a_logged_in_user(client, login):
    login()
    assert client.get("/").status_code == 200
    assert client.get(reverse(LIST_URL)).status_code == 200
    assert client.get(reverse(CREATE_URL)).status_code == 200

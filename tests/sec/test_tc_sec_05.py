import pytest
from django.urls import reverse

from tasks.models import Task


pytestmark = pytest.mark.django_db


def test_task_input_is_escaped_in_html(client, make_user):
    owner = make_user()
    client.force_login(owner)
    payload = "<script>alert('x')</script>"

    response = client.post(
        reverse("tasks:create"),
        {
            "title": payload,
            "description": payload,
            "due_date": "",
            "priority": "medium",
            "labels": [],
        },
    )

    assert response.status_code == 302
    response = client.get(reverse("tasks:list"))
    assert payload.encode() not in response.content
    assert b"&lt;script&gt;" in response.content


def test_state_changing_attachment_request_requires_csrf(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Task")
    client.force_login(owner)
    client.handler.enforce_csrf_checks = True

    response = client.post(reverse("storage:upload", args=[task.pk]), {})

    assert response.status_code == 403

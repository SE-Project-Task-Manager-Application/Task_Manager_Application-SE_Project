"""TC-Org-02: task list label/date filtering and ordering."""

from datetime import date, datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from tasks.models import Label, Task

pytestmark = pytest.mark.django_db


def test_filter_by_label_and_date_and_sort_both_directions(client, make_user):
    owner = make_user()
    client.force_login(owner)
    label = Label.objects.create(name="Release")
    first = Task.objects.create(
        owner=owner, title="Alpha", due_date=timezone.make_aware(datetime(2026, 11, 5, 9, 0))
    )
    first.labels.add(label)
    Task.objects.create(
        owner=owner, title="Zulu", due_date=timezone.make_aware(datetime(2026, 11, 6, 9, 0))
    )

    filtered = client.get(
        reverse("tasks:list"),
        {"label": "Release", "due_date": date(2026, 11, 5).isoformat()},
    )
    html = filtered.content.decode()
    assert "Alpha" in html and "Zulu" not in html

    ascending = client.get(
        reverse("tasks:list"), {"show": "all", "sort": "title", "direction": "asc"}
    )
    descending = client.get(
        reverse("tasks:list"), {"show": "all", "sort": "title", "direction": "desc"}
    )
    assert ascending.content.decode().find("Alpha") < ascending.content.decode().find("Zulu")
    assert descending.content.decode().find("Zulu") < descending.content.decode().find("Alpha")

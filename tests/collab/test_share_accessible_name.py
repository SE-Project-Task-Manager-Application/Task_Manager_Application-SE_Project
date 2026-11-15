"""Regression: task sharing keeps its visible label in its accessible name."""

from html.parser import HTMLParser

import pytest
from django.urls import reverse

from tasks.models import Task


class SummaryNames(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = []

    def handle_starttag(self, tag, attrs):
        if tag == "summary":
            self.names.append(dict(attrs).get("aria-label"))


@pytest.mark.django_db
@pytest.mark.parametrize(
    "title",
    ["Weekly report", 'Quotes " & <script>alert(1)</script>', "日本語のタスク"],
)
def test_share_summary_label_includes_visible_text_and_task_title(client, make_user, title):
    owner = make_user()
    Task.objects.create(owner=owner, title=title)
    client.force_login(owner)

    response = client.get(reverse("tasks:list"))

    assert response.status_code == 200
    names = SummaryNames()
    names.feed(response.content.decode())
    assert f"Share task {title}" in names.names
    assert "<script>alert(1)</script>" not in response.content.decode()

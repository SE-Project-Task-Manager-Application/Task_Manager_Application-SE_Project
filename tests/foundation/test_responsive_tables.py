"""Keep responsive task rows labeled and table semantics explicit across roles."""

from html.parser import HTMLParser

import pytest

from collab.models import TaskShare
from tasks.models import Task


class TableMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.mark.django_db
@pytest.mark.parametrize("path,columns", [
    ("/tasks/", ["Status", "Priority", "Due", "Assigned to", "Labels", "Access", "Actions"]),
    ("/dashboard/", ["Status", "Priority", "Due", "Assigned to", "Labels"]),
])
@pytest.mark.parametrize("as_viewer", [False, True])
def test_responsive_rows_keep_labels_and_table_roles(client, make_user, path, columns, as_viewer):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="A readable task")
    user = owner
    if as_viewer:
        user = make_user()
        TaskShare.objects.create(task=task, user=user, permission="viewer", shared_by=owner)
    client.force_login(user)

    response = client.get(path)
    assert response.status_code == 200
    markup = TableMarkup()
    markup.feed(response.content.decode())
    tables = [attrs for tag, attrs in markup.elements if tag == "table"]
    assert len(tables) == 1
    assert tables[0].get("role") == "table"
    assert "responsive-table" in tables[0].get("class", "").split()
    cells = [attrs for tag, attrs in markup.elements if tag == "td"]
    assert [attrs.get("data-label") for attrs in cells] == columns
    assert all(attrs.get("role") == "cell" for attrs in cells)
    headers = [attrs for tag, attrs in markup.elements if tag == "th"]
    assert all(
        attrs.get("role") == "columnheader"
        for attrs in headers if attrs.get("scope") == "col"
    )
    assert any(
        attrs.get("role") == "rowheader" and attrs.get("scope") == "row" for attrs in headers
    )

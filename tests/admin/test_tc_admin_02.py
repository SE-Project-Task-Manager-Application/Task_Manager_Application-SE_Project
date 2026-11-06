"""TC-Admin-02: manage categories (TM-F-051).

SRS 4.6: an administrator can create, rename or archive global categories.
SAD: archived categories are hidden at task creation but stay on existing tasks.
"""

import pytest
from django.test import Client
from django.urls import reverse

from adminpanel.models import AuditRecord
from tasks.models import Label, Task

pytestmark = pytest.mark.django_db

LIST_URL = "adminpanel:category_list"

NON_ADMIN_REQUESTS = [
    ("get", "category_list", False),
    ("post", "category_list", False),
    ("get", "category_rename", True),
    ("post", "category_rename", True),
    ("post", "category_archive", True),
    ("post", "category_restore", True),
]


@pytest.fixture
def admin_client(client, make_user):
    client.force_login(make_user(role="admin"))
    return client


def _audit(action, label):
    return AuditRecord.objects.filter(
        action=action, target_type="label", target_id=str(label.pk)
    )


def _member_client(member):
    member_client = Client()
    member_client.force_login(member)
    return member_client


def test_admin_sees_active_and_archived_categories(admin_client):
    Label.objects.create(name="Bug")
    Label.objects.create(name="Legacy", is_archived=True)
    response = admin_client.get(reverse(LIST_URL))
    html = response.content.decode()
    assert response.status_code == 200
    assert "Bug" in html and "Legacy" in html
    assert "Archived" in html


def test_admin_can_create_a_category_and_it_is_audited(admin_client):
    response = admin_client.post(reverse(LIST_URL), {"name": "  Backend  "}, follow=True)
    label = Label.objects.get()
    assert label.name == "Backend" and not label.is_archived
    assert _audit("label.created", label).exists()
    assert "Backend" in response.content.decode()


def test_duplicate_name_is_rejected_ignoring_case(admin_client):
    Label.objects.create(name="Backend")
    response = admin_client.post(reverse(LIST_URL), {"name": "bAcKeNd"})
    assert response.status_code == 200
    assert "already exists" in response.content.decode()
    assert Label.objects.count() == 1
    assert not AuditRecord.objects.filter(action="label.created").exists()


def test_blank_name_is_rejected(admin_client):
    response = admin_client.post(reverse(LIST_URL), {"name": "   "})
    assert response.status_code == 200
    assert Label.objects.count() == 0


def test_admin_can_rename_a_category_and_it_is_audited(admin_client):
    label = Label.objects.create(name="Bug")
    url = reverse("adminpanel:category_rename", args=[label.pk])
    response = admin_client.post(url, {"name": "Defect"})
    assert response.status_code == 302
    label.refresh_from_db()
    assert label.name == "Defect"
    record = _audit("label.renamed", label).get()
    assert record.details == {"old_name": "Bug", "new_name": "Defect"}


def test_rename_to_an_existing_name_is_rejected(admin_client):
    Label.objects.create(name="Bug")
    other = Label.objects.create(name="Feature")
    url = reverse("adminpanel:category_rename", args=[other.pk])
    response = admin_client.post(url, {"name": "bug"})
    assert response.status_code == 200
    other.refresh_from_db()
    assert other.name == "Feature"
    assert not _audit("label.renamed", other).exists()


def test_rename_page_loads_and_unchanged_name_is_not_audited(admin_client):
    label = Label.objects.create(name="Bug")
    url = reverse("adminpanel:category_rename", args=[label.pk])
    assert admin_client.get(url).status_code == 200
    admin_client.post(url, {"name": "Bug"})
    assert not _audit("label.renamed", label).exists()


def test_archived_category_hidden_at_creation_but_kept_on_tasks(admin_client, make_user):
    member = make_user(email="member@example.com")
    label = Label.objects.create(name="Hidden-cat")
    Label.objects.create(name="Shown-cat")
    task = Task.objects.create(owner=member, title="Existing")
    task.labels.add(label)

    response = admin_client.post(reverse("adminpanel:category_archive", args=[label.pk]))

    assert response.status_code == 302
    label.refresh_from_db()
    assert label.is_archived
    assert _audit("label.archived", label).exists()
    member_client = _member_client(member)
    form_page = member_client.get(reverse("tasks:create")).content.decode()
    assert "Shown-cat" in form_page and "Hidden-cat" not in form_page
    assert "Hidden-cat" in member_client.get(reverse("tasks:list")).content.decode()
    assert task.labels.filter(pk=label.pk).exists()


def test_restoring_makes_the_category_available_again(admin_client, make_user):
    member = make_user(email="member@example.com")
    label = Label.objects.create(name="Old-cat", is_archived=True)

    response = admin_client.post(reverse("adminpanel:category_restore", args=[label.pk]))

    assert response.status_code == 302
    label.refresh_from_db()
    assert not label.is_archived
    assert _audit("label.restored", label).exists()
    form_page = _member_client(member).get(reverse("tasks:create")).content.decode()
    assert "Old-cat" in form_page


def test_archiving_twice_writes_one_audit_record(admin_client):
    label = Label.objects.create(name="Bug")
    url = reverse("adminpanel:category_archive", args=[label.pk])
    admin_client.post(url)
    admin_client.post(url)
    assert _audit("label.archived", label).count() == 1


def test_archive_and_restore_reject_get(admin_client):
    label = Label.objects.create(name="Bug")
    for name in ("category_archive", "category_restore"):
        response = admin_client.get(reverse(f"adminpanel:{name}", args=[label.pk]))
        assert response.status_code == 405


def test_unknown_category_returns_404(admin_client):
    response = admin_client.post(reverse("adminpanel:category_archive", args=[9999]))
    assert response.status_code == 404


@pytest.mark.parametrize(("method", "name", "needs_label"), NON_ADMIN_REQUESTS)
def test_non_admin_cannot_manage_categories(client, make_user, method, name, needs_label):
    client.force_login(make_user(email="member@example.com"))
    label = Label.objects.create(name="Keep")
    url = reverse(f"adminpanel:{name}", args=[label.pk] if needs_label else [])

    response = getattr(client, method)(url, {"name": "Hacked"} if method == "post" else {})

    assert response.status_code == 403
    label.refresh_from_db()
    assert label.name == "Keep" and not label.is_archived
    assert Label.objects.count() == 1
    assert not AuditRecord.objects.filter(action__startswith="label.").exists()


def test_anonymous_user_is_sent_to_login(client):
    response = client.get(reverse(LIST_URL))
    assert response.status_code == 302
    assert reverse("accounts:login") in response["Location"]

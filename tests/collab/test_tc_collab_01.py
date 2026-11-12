"""TC-Collab-01: share tasks with Viewer and Editor access."""

import pytest
from django.urls import reverse
from django.utils import timezone

from adminpanel.models import AuditRecord
from collab.models import TaskShare
from tasks.models import Task, TaskAssignment

pytestmark = pytest.mark.django_db

SHARE_URL = "tasks:share"
LIST_URL = "tasks:list"


def _share(client, task, email, permission="viewer"):
    return client.post(
        reverse(SHARE_URL, args=[task.pk]),
        {"email": email, "permission": permission},
        follow=True,
    )


@pytest.mark.parametrize("permission,label", [("viewer", "Viewer"), ("editor", "Editor")])
def test_owner_can_share_task_and_recipient_sees_permission(
    client, make_user, permission, label
):
    owner, recipient = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Shared report")
    client.force_login(owner)

    response = _share(client, task, recipient.email, permission)

    share = TaskShare.objects.get(task=task, user=recipient)
    assert share.permission == permission
    assert "Shared report" in response.content.decode()
    client.force_login(recipient)
    assert label in client.get(reverse(LIST_URL)).content.decode()
    audit = AuditRecord.objects.get(action="task.shared")
    assert audit.actor == owner
    assert audit.target_type == "task" and audit.target_id == str(task.pk)


def test_owner_sees_recipient_and_permission_in_task_list(client, make_user):
    owner, recipient = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Quarterly plan")
    TaskShare.objects.create(
        task=task, user=recipient, permission=TaskShare.Permission.EDITOR, shared_by=owner
    )
    client.force_login(owner)

    html = client.get(reverse(LIST_URL)).content.decode()

    assert recipient.email in html and "Editor" in html


def test_non_owner_who_can_view_gets_forbidden_on_share_post(client, make_user):
    owner, viewer, editor = make_user(), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Protected task")
    TaskShare.objects.create(
        task=task, user=viewer, permission="viewer", shared_by=owner
    )
    TaskShare.objects.create(
        task=task, user=editor, permission="editor", shared_by=owner
    )

    for non_owner in (viewer, editor):
        client.force_login(non_owner)
        assert _share(client, task, make_user().email).status_code == 403


def test_inaccessible_and_missing_task_ids_both_return_not_found(client, make_user):
    owner, stranger, recipient = make_user(), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Private task")
    TaskShare.objects.create(task=task, user=recipient, permission="viewer", shared_by=owner)
    client.force_login(stranger)

    hidden = client.post(reverse(SHARE_URL, args=[task.pk]), {})
    missing = client.post(reverse(SHARE_URL, args=[task.pk + 9999]), {})

    assert hidden.status_code == missing.status_code == 404


@pytest.mark.parametrize("target", ["self", "unknown", "disabled", "deleted", "deleted_task"])
def test_invalid_share_targets_are_rejected_without_creating_share(
    client, make_user, target
):
    owner = make_user()
    recipient = make_user(is_active=False) if target == "disabled" else make_user()
    if target == "deleted":
        recipient.deleted_at = timezone.now()
        recipient.save(update_fields=["deleted_at"])
    task = Task.objects.create(owner=owner, title="Share candidate")
    if target == "deleted_task":
        task.soft_delete()
    email = {
        "self": owner.email,
        "unknown": "missing@example.com",
        "disabled": recipient.email,
        "deleted": recipient.email,
        "deleted_task": recipient.email,
    }[target]
    client.force_login(owner)

    response = client.post(
        reverse(SHARE_URL, args=[task.pk]), {"email": email, "permission": "viewer"}
    )

    expected_status = 404 if target == "deleted_task" else 302
    assert response.status_code == expected_status
    assert not TaskShare.objects.filter(task=task).exists()


def test_ambiguous_case_insensitive_email_is_handled_as_validation_error(client, make_user):
    owner = make_user()
    recipient = make_user()
    other_case = type(recipient).objects.create(email=recipient.email.upper())
    task = Task.objects.create(owner=owner, title="Ambiguous recipient")
    client.force_login(owner)

    response = client.post(
        reverse(SHARE_URL, args=[task.pk]),
        {"email": recipient.email, "permission": "viewer"},
        follow=True,
    )

    assert response.status_code == 200
    assert "More than one account matches" in response.content.decode()
    assert not TaskShare.objects.filter(task=task).exists()
    assert recipient.pk != other_case.pk


def test_permission_change_updates_one_share_and_audits_only_real_changes(client, make_user):
    owner, recipient = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Change access")
    client.force_login(owner)

    _share(client, task, recipient.email, "viewer")
    first_shared_at = TaskShare.objects.get(task=task, user=recipient).shared_at
    _share(client, task, recipient.email, "editor")
    _share(client, task, recipient.email, "editor")

    share = TaskShare.objects.get(task=task, user=recipient)
    assert TaskShare.objects.filter(task=task, user=recipient).count() == 1
    assert share.permission == "editor" and share.shared_at == first_shared_at
    assert AuditRecord.objects.filter(action="task.shared").count() == 1
    assert AuditRecord.objects.filter(action="task.share_updated").count() == 1
    actors = AuditRecord.objects.filter(target_id=str(task.pk)).values_list("actor_id", flat=True)
    assert list(actors) == [owner.pk, owner.pk]


def test_share_requires_login_and_rejects_get(client, make_user):
    task = Task.objects.create(owner=make_user(), title="Methods")

    anonymous = client.post(reverse(SHARE_URL, args=[task.pk]), {})
    assert anonymous.status_code == 302
    assert anonymous["Location"].startswith("/accounts/login/?next=")
    client.force_login(task.owner)
    assert client.get(reverse(SHARE_URL, args=[task.pk])).status_code == 405


def test_visibility_and_edit_access_follow_owner_assignment_and_share_permissions(make_user):
    owner, assignee, viewer, editor, stranger = [make_user() for _ in range(5)]
    task = Task.objects.create(owner=owner, title="Access policy")
    TaskAssignment.objects.create(task=task, user=assignee, assigned_by=owner)
    TaskShare.objects.create(task=task, user=viewer, permission="viewer", shared_by=owner)
    TaskShare.objects.create(task=task, user=editor, permission="editor", shared_by=owner)
    def visible_ids(user):
        return set(Task.objects.active().visible_to(user).values_list("pk", flat=True))

    def editable_ids(user):
        return set(Task.objects.active().editable_by(user).values_list("pk", flat=True))

    assert all(task.pk in visible_ids(user) for user in (owner, assignee, viewer, editor))
    assert task.pk not in visible_ids(stranger)
    assert all(task.pk in editable_ids(user) for user in (owner, assignee, editor))
    assert task.pk not in editable_ids(viewer)
    assert task.pk not in editable_ids(stranger)


def test_soft_deleted_owner_keeps_shares_valid_and_protected_reference(client, make_user):
    admin, owner, recipient = make_user("admin"), make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Retained share")
    share = TaskShare.objects.create(
        task=task, user=recipient, permission="viewer", shared_by=owner
    )
    client.force_login(admin)

    response = client.post(reverse("adminpanel:delete_user", args=[owner.pk]))

    owner.refresh_from_db()
    share.refresh_from_db()
    assert response.status_code == 302
    assert owner.deleted_at is not None and not owner.is_active
    assert share.shared_by_id == owner.pk
    client.force_login(recipient)
    assert "Retained share" in client.get(reverse(LIST_URL)).content.decode()

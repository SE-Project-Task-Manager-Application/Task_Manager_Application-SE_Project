"""TC-Collab-03: revoke a collaborator's access to a task."""

import pytest
from django.urls import reverse

from adminpanel.models import AuditRecord
from collab.models import TaskShare
from tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("permission", ["viewer", "editor"])
def test_owner_revokes_access_on_next_request_and_audits_change(
    client, make_user, permission
):
    owner, collaborator = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Shared report")
    share = TaskShare.objects.create(
        task=task, user=collaborator, permission=permission, shared_by=owner
    )
    revoke_url = reverse("tasks:revoke_share", args=[task.pk, share.pk])
    client.force_login(owner)

    response = client.post(revoke_url, follow=True)

    assert response.status_code == 200
    assert not TaskShare.objects.filter(pk=share.pk).exists()
    audit = AuditRecord.objects.get(action="task.share_revoked")
    assert audit.actor == owner
    assert audit.target_type == "task" and audit.target_id == str(task.pk)
    assert audit.details == {"user_id": collaborator.pk, "permission": permission}

    client.force_login(collaborator)
    visible_ids = Task.objects.active().visible_to(collaborator).values_list("pk", flat=True)
    assert task.pk not in visible_ids
    assert "Shared report" not in client.get(reverse("tasks:list")).content.decode()
    assert client.get(reverse("tasks:edit", args=[task.pk])).status_code == 403


def test_only_owner_can_revoke_and_get_is_not_allowed(client, make_user):
    owner, collaborator = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Protected report")
    share = TaskShare.objects.create(
        task=task, user=collaborator, permission="viewer", shared_by=owner
    )
    revoke_url = reverse("tasks:revoke_share", args=[task.pk, share.pk])

    anonymous = client.post(revoke_url)
    assert anonymous.status_code == 302
    client.force_login(collaborator)
    assert client.post(revoke_url).status_code == 404
    assert client.get(revoke_url).status_code == 405
    assert TaskShare.objects.filter(pk=share.pk).exists()
    assert not AuditRecord.objects.filter(action="task.share_revoked").exists()


def test_owner_can_revoke_access_for_a_soft_deleted_task(client, make_user):
    owner, collaborator = make_user(), make_user()
    task = Task.objects.create(owner=owner, title="Deleted report")
    share = TaskShare.objects.create(
        task=task, user=collaborator, permission="viewer", shared_by=owner
    )
    task.soft_delete()
    client.force_login(owner)

    response = client.post(reverse("tasks:revoke_share", args=[task.pk, share.pk]))

    assert response.status_code == 302
    assert not TaskShare.objects.filter(pk=share.pk).exists()
    assert AuditRecord.objects.filter(
        action="task.share_revoked", target_id=str(task.pk)
    ).exists()

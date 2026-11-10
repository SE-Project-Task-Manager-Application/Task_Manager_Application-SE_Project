import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from adminpanel.models import AuditRecord
from tasks.models import Task
from storage.models import TaskAttachment


pytestmark = pytest.mark.django_db


def test_owner_can_upload_and_download_attachment(client, make_user, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = make_user()
        task = Task.objects.create(owner=owner, title="Task")
        client.force_login(owner)

        upload = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
        response = client.post(reverse("storage:upload", args=[task.pk]), {"file": upload})

        assert response.status_code == 302
        attachment = TaskAttachment.objects.get(task=task)
        assert attachment.original_name == "notes.txt"
        assert AuditRecord.objects.filter(action="task.attachment_added").exists()

        response = client.get(reverse("storage:download", args=[attachment.pk]))
        assert response.status_code == 200
        assert response["Content-Disposition"].startswith("attachment;")
        assert b"".join(response.streaming_content) == b"hello"


def test_attachment_rejects_oversize_and_eicar(client, make_user):
    owner = make_user()
    task = Task.objects.create(owner=owner, title="Task")
    client.force_login(owner)

    oversized = SimpleUploadedFile("large.txt", b"x" * (10 * 1024 * 1024 + 1))
    client.post(reverse("storage:upload", args=[task.pk]), {"file": oversized})
    assert not TaskAttachment.objects.exists()

    marker = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    infected = SimpleUploadedFile("virus.txt", marker)
    client.post(reverse("storage:upload", args=[task.pk]), {"file": infected})
    assert not TaskAttachment.objects.exists()

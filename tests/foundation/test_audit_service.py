"""S-05: AuditService and the append-only audit record."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from adminpanel.models import AuditImmutableError, AuditRecord
from adminpanel.services import AuditService
from tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def task(make_user):
    return Task.objects.create(owner=make_user(), title="t")


def test_record_writes_a_row_for_a_model_target(make_user, task):
    actor = make_user()
    record = AuditService.record(actor, "task.created", task, details={"priority": "high"})
    record.refresh_from_db()
    assert record.actor == actor
    assert record.action == "task.created"
    assert record.target_type == "task"
    assert record.target_id == str(task.pk)
    assert record.details == {"priority": "high"}


def test_record_accepts_a_type_and_id_pair():
    record = AuditService.record(None, "user.login_failed", ("user", 7))
    assert (record.target_type, record.target_id, record.actor) == ("user", "7", None)


def test_timestamp_defaults_to_now_in_utc():
    before = datetime.now(UTC)
    record = AuditService.record(None, "system.job_ran", ("job", "x"))
    assert before <= record.created_at <= datetime.now(UTC) + timedelta(seconds=1)
    assert record.created_at.utcoffset() == timedelta(0)


def test_given_timestamp_is_stored_as_utc():
    ist = timezone(timedelta(hours=5, minutes=30))
    record = AuditService.record(None, "system.job_ran", ("job", "x"),
                                 timestamp=datetime(2026, 10, 15, 12, 0, tzinfo=ist))
    record.refresh_from_db()
    assert record.created_at == datetime(2026, 10, 15, 6, 30, tzinfo=UTC)


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValueError):
        AuditService.record(None, "system.job_ran", ("job", "x"), timestamp=datetime(2026, 1, 1))


@pytest.mark.parametrize("bad", ["", "created", "Task.Created", "task..created", "task.created!"])
def test_invalid_action_names_are_rejected(bad):
    with pytest.raises(ValueError):
        AuditService.record(None, bad, ("task", 1))


def test_unsaved_target_is_rejected(make_user):
    with pytest.raises(ValueError):
        AuditService.record(None, "task.created", Task(owner=make_user(), title="x"))


def test_secrets_in_details_are_redacted(task):
    record = AuditService.record(
        None, "user.updated", task,
        details={"password": "hunter2", "nested": {"reset_token": "abc"}, "status": "done"},
    )
    assert record.details == {
        "password": "[redacted]", "nested": {"reset_token": "[redacted]"}, "status": "done",
    }


def test_existing_row_cannot_be_modified(task):
    record = AuditService.record(None, "task.created", task)
    record.action = "task.deleted"
    with pytest.raises(AuditImmutableError):
        record.save()
    record.refresh_from_db()
    assert record.action == "task.created"


def test_rows_cannot_be_deleted_or_bulk_changed(task):
    record = AuditService.record(None, "task.created", task)
    with pytest.raises(AuditImmutableError):
        record.delete()
    with pytest.raises(AuditImmutableError):
        AuditRecord.objects.all().delete()
    with pytest.raises(AuditImmutableError):
        AuditRecord.objects.all().update(action="x.y")
    assert AuditRecord.objects.count() == 1


def test_audit_service_can_be_called_from_a_view(client, make_user, task):
    """Done-when: callable from a view as well as from a test."""
    from django.http import HttpResponse
    from django.test import RequestFactory

    def view(request):
        AuditService.record(None, "task.viewed", task)
        return HttpResponse("ok")

    assert view(RequestFactory().get("/")).status_code == 200
    assert AuditRecord.objects.filter(action="task.viewed").count() == 1

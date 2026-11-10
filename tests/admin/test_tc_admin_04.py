import pytest
from django.urls import reverse

from adminpanel.models import AuditRecord, SystemConfig


pytestmark = pytest.mark.django_db


def test_admin_can_update_system_config_and_audit_it(client, make_user):
    admin = make_user(role="admin")
    client.force_login(admin)

    response = client.post(
        reverse("adminpanel:update_system_config"),
        {
            "password_min_length": 12,
            "session_timeout_seconds": 1800,
            "notifications_enabled": "",
            "notification_sender": "alerts@example.com",
        },
    )

    assert response.status_code == 302
    config = SystemConfig.objects.get()
    assert config.password_min_length == 12
    assert config.session_timeout_seconds == 1800
    assert not config.notifications_enabled
    assert AuditRecord.objects.filter(action="system_config.updated", actor=admin).exists()


def test_member_cannot_update_system_config(client, make_user):
    member = make_user()
    client.force_login(member)

    response = client.get(reverse("adminpanel:system_config"))

    assert response.status_code == 403

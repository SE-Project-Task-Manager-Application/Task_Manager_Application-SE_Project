from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.urls import reverse


def test_tc_auth_06_logout_invalidates_session_and_requires_post(
    client, make_user
):
    user = make_user(email="logout@example.com")
    client.force_login(user)

    tasks_url = reverse("tasks:list")
    logout_url = reverse("accounts:logout")
    old_session_key = client.cookies[settings.SESSION_COOKIE_NAME].value

    page = client.get(tasks_url)
    assert page.status_code == 200
    assertContains = page.content
    assert f'<form method="post" action="{logout_url}"'.encode() in assertContains
    assert b'name="csrfmiddlewaretoken"' in assertContains

    response = client.post(logout_url)
    assert response.status_code == 302
    assert response.url == reverse("home")
    assert not Session.objects.filter(session_key=old_session_key).exists()

    replay_client = Client()
    replay_client.cookies[settings.SESSION_COOKIE_NAME] = old_session_key
    response = replay_client.get(tasks_url)

    assert response.status_code == 302
    assert response.url.startswith(reverse("accounts:login"))
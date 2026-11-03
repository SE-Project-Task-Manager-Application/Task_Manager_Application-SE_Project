"""TC-Auth-05 (TM-F-005): edit profile (name, email, avatar) and change password."""

import re
import time
from unittest import mock

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tests.conftest import TEST_PASSWORD

PROFILE = "accounts:profile"


@pytest.fixture(autouse=True)
def _temp_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path  # uploads never touch the repo folder

NEW_PASSWORD = "Another-pass-4242"


def _login(client, user):
    client.force_login(user)
    return user


def test_profile_requires_login(client):
    response = client.get(reverse(PROFILE))
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_name_saves_and_shows_immediately(client, make_user):
    user = _login(client, make_user())
    response = client.post(
        reverse(PROFILE), {"save_profile": "1", "full_name": "Asha Rao"}, follow=True
    )
    user.refresh_from_db()
    assert user.full_name == "Asha Rao"
    assert 'value="Asha Rao"' in response.content.decode()


def test_avatar_upload_accepts_png_and_rejects_other_types(client, make_user):
    user = _login(client, make_user())
    bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
    resp = client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": bad})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert not user.avatar

    good = SimpleUploadedFile("me.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
    client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": good})
    user.refresh_from_db()
    assert user.avatar.name.endswith(".png")


def test_avatar_over_10mb_is_rejected(client, make_user):
    user = _login(client, make_user())
    big = SimpleUploadedFile("big.png", b"0" * (10 * 1024 * 1024 + 1), content_type="image/png")
    resp = client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": big})
    assert resp.status_code == 200
    user.refresh_from_db()
    assert not user.avatar


def test_email_changes_only_after_confirmation_link(client, make_user):
    user = _login(client, make_user(email="old@example.com"))
    client.post(reverse(PROFILE), {"new_email": "New@Example.com"})
    user.refresh_from_db()
    assert user.email == "old@example.com"  # not changed yet
    assert mail.outbox[0].to == ["new@example.com"]

    link = re.search(r"https?://\S+/accounts/profile/email/confirm/\S+/", mail.outbox[0].body)
    client.get(link.group(0).split("testserver", 1)[1])
    user.refresh_from_db()
    assert user.email == "new@example.com"


def test_email_link_cannot_be_used_by_another_user(client, make_user):
    owner = make_user(email="a@example.com")
    other = make_user(email="b@example.com")
    client.force_login(owner)
    client.post(reverse(PROFILE), {"new_email": "c@example.com"})
    link = re.search(r"/accounts/profile/email/confirm/\S+/", mail.outbox[0].body).group(0)
    client.force_login(other)
    client.get(link)
    other.refresh_from_db()
    assert other.email == "b@example.com"


def test_email_already_taken_is_rejected(client, make_user):
    make_user(email="taken@example.com")
    _login(client, make_user(email="me@example.com"))
    resp = client.post(reverse(PROFILE), {"new_email": "taken@example.com"})
    assert resp.status_code == 200
    assert mail.outbox == []


def test_expired_email_link_is_rejected(client, make_user):
    user = _login(client, make_user(email="old@example.com"))
    client.post(reverse(PROFILE), {"new_email": "new@example.com"})
    link = re.search(r"/accounts/profile/email/confirm/\S+/", mail.outbox[0].body).group(0)
    with mock.patch("time.time", return_value=time.time() + 25 * 3600):
        client.get(link)
    user.refresh_from_db()
    assert user.email == "old@example.com"


def test_change_password_needs_current_password_and_keeps_session(client, make_user):
    user = _login(client, make_user())
    url = reverse("accounts:password_change")
    wrong = client.post(
        url, {"old_password": "nope", "new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}
    )
    assert wrong.status_code == 200
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)

    ok = client.post(
        url,
        {
            "old_password": TEST_PASSWORD,
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        },
    )
    assert ok.status_code == 302
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert client.get(reverse(PROFILE)).status_code == 200  # still logged in


def test_profile_link_in_navigation(client, make_user):
    _login(client, make_user())
    assert reverse(PROFILE) in client.get(reverse("tasks:list")).content.decode()


def test_email_link_cannot_be_replayed_after_use(client, make_user):
    user = _login(client, make_user(email="old@example.com"))
    client.post(reverse(PROFILE), {"new_email": "new@example.com"})
    client.post(reverse(PROFILE), {"new_email": "other@example.com"})
    first, second = (
        re.search(r"/accounts/profile/email/confirm/\S+/", m.body).group(0) for m in mail.outbox
    )
    client.get(first)
    user.refresh_from_db()
    assert user.email == "new@example.com"

    client.get(second)  # an older, still-unexpired link no longer matches the current email
    client.get(first)
    user.refresh_from_db()
    assert user.email == "new@example.com"


def test_own_avatar_is_served_and_needs_login(client, make_user):
    user = _login(client, make_user())
    png = SimpleUploadedFile("me.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
    client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": png})
    response = client.get(reverse("accounts:avatar"))
    assert response.status_code == 200
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    assert reverse("accounts:avatar") in client.get(reverse(PROFILE)).content.decode()

    client.logout()
    assert client.get(reverse("accounts:avatar")).status_code == 302
    other = _login(client, make_user())
    assert other.pk != user.pk
    assert client.get(reverse("accounts:avatar")).status_code == 404


def test_avatar_with_image_extension_but_other_content_is_rejected(client, make_user):
    user = _login(client, make_user())
    fake = SimpleUploadedFile("x.png", b"MZ\x90\x00not an image", content_type="image/png")
    resp = client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": fake})
    assert resp.status_code == 200
    assert "not a valid" in resp.content.decode()
    user.refresh_from_db()
    assert not user.avatar


def test_avatar_content_must_match_extension(client, make_user):
    user = _login(client, make_user())
    png_as_gif = SimpleUploadedFile("x.gif", b"\x89PNG\r\n\x1a\n", content_type="image/gif")
    client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": png_as_gif})
    user.refresh_from_db()
    assert not user.avatar


@pytest.mark.parametrize(
    "name,data",
    [("a.jpg", b"\xff\xd8\xff\xe0\x00\x10JFIF"), ("a.gif", b"GIF89a\x01\x00")],
)
def test_avatar_jpeg_and_gif_are_accepted(client, make_user, name, data):
    user = _login(client, make_user())
    f = SimpleUploadedFile(name, data, content_type="application/octet-stream")
    client.post(reverse(PROFILE), {"save_profile": "1", "full_name": "A", "avatar": f})
    user.refresh_from_db()
    assert user.avatar.name.endswith(name.split(".")[1])


def test_email_change_reports_failure_when_mail_cannot_be_sent(client, make_user):
    user = _login(client, make_user(email="old@example.com"))
    with mock.patch("accounts.views.NotificationService.send", return_value=False):
        resp = client.post(reverse(PROFILE), {"new_email": "new@example.com"}, follow=True)
    text = resp.content.decode()
    assert "could not send the confirmation email" in text
    assert "We sent a confirmation link" not in text
    user.refresh_from_db()
    assert user.email == "old@example.com"


def test_email_change_success_message_only_when_sent(client, make_user):
    _login(client, make_user(email="old@example.com"))
    resp = client.post(reverse(PROFILE), {"new_email": "new@example.com"}, follow=True)
    assert "We sent a confirmation link to new@example.com" in resp.content.decode()
    assert len(mail.outbox) == 1

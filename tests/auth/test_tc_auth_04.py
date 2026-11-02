"""TC-Auth-04 (TM-F-004): password reset by a time-limited, single-use e-mail link."""

import re
from datetime import timedelta
from unittest import mock

from django.core import mail
from django.urls import reverse

from tests.conftest import TEST_PASSWORD

NEW_PASSWORD = "Brand-new-pass-77"


def _request_reset(client, email):
    return client.post(reverse("accounts:password_reset"), {"email": email})


def _link_from_outbox():
    assert len(mail.outbox) == 1
    match = re.search(r"https?://\S+/accounts/reset/\S+/", mail.outbox[0].body)
    assert match, mail.outbox[0].body
    return match.group(0).split("testserver", 1)[1]


def test_reset_link_is_emailed_and_sets_new_password(client, make_user):
    user = make_user(email="reset@example.com")
    response = _request_reset(client, "reset@example.com")
    assert response.status_code == 302
    assert mail.outbox[0].to == ["reset@example.com"]

    link = _link_from_outbox()
    page = client.get(link, follow=True)  # Django swaps the token for a session URL
    form_url = page.redirect_chain[-1][0]
    done = client.post(form_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})
    assert done.status_code == 302

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(TEST_PASSWORD)


def test_link_works_only_once(client, make_user):
    make_user(email="once@example.com")
    _request_reset(client, "once@example.com")
    link = _link_from_outbox()
    form_url = client.get(link, follow=True).redirect_chain[-1][0]
    client.post(form_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

    second = client.get(link, follow=True)
    assert second.context["validlink"] is False


def test_link_expires_after_30_minutes(client, make_user):
    make_user(email="late@example.com")
    _request_reset(client, "late@example.com")
    link = _link_from_outbox()

    from django.contrib.auth.tokens import default_token_generator as gen

    real_now = gen._now()
    with mock.patch.object(type(gen), "_now", return_value=real_now + timedelta(minutes=31)):
        page = client.get(link, follow=True)
    assert page.context["validlink"] is False


def test_unknown_email_gets_same_response_and_no_mail(client, db):
    response = _request_reset(client, "nobody@example.com")
    assert response.status_code == 302
    assert response.url == reverse("accounts:password_reset_done")
    assert mail.outbox == []


def test_inactive_and_deleted_accounts_get_no_mail(client, make_user):
    from django.utils import timezone

    make_user(email="off@example.com", is_active=False)
    make_user(email="gone@example.com", deleted_at=timezone.now())
    _request_reset(client, "off@example.com")
    _request_reset(client, "gone@example.com")
    assert mail.outbox == []


def test_weak_new_password_is_rejected(client, make_user):
    user = make_user(email="weak@example.com")
    _request_reset(client, "weak@example.com")
    form_url = client.get(_link_from_outbox(), follow=True).redirect_chain[-1][0]
    response = client.post(form_url, {"new_password1": "12345678", "new_password2": "12345678"})
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


def test_login_page_links_to_reset(client, db):
    page = client.get(reverse("accounts:login")).content.decode()
    assert reverse("accounts:password_reset") in page

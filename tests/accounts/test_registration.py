"""Registration regressions, including the post/redirect/get fix for bug #61."""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def registration_data(email="new.member@example.com", password="Violet-river-4827!"):
    return {"email": email, "password1": password, "password2": password}


def test_success_redirects_and_refresh_does_not_resubmit(client):
    response = client.post(reverse("accounts:register"), registration_data())

    assert response.status_code == 302
    assert response.url == reverse("accounts:registration_success")
    assert "new.member@example.com" not in response.url
    assert get_user_model().objects.count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new.member@example.com"]
    assert mail.outbox[0].subject == "Task Manager account confirmation"
    assert "new.member@example.com" in mail.outbox[0].body

    # Each refresh is a GET of the redirect target, never another form POST.
    for _ in range(3):
        refreshed = client.get(response.url)
        assert refreshed.status_code == 200
        assert "Your account for new.member@example.com has been created." in refreshed.text
        assert "already exists" not in refreshed.text
    assert get_user_model().objects.count() == 1
    assert len(mail.outbox) == 1


def test_success_page_without_registration_redirects_to_form(client):
    response = client.get(reverse("accounts:registration_success"))
    assert response.status_code == 302
    assert response.url == reverse("accounts:register")


def test_success_page_does_not_accept_posts(client):
    response = client.post(reverse("accounts:registration_success"), registration_data())
    assert response.status_code == 405
    assert not get_user_model().objects.exists()


def test_success_email_is_session_scoped(client):
    from django.test import Client

    client.post(reverse("accounts:register"), registration_data())
    response = Client().get(reverse("accounts:registration_success"))
    assert response.status_code == 302
    assert response.url == reverse("accounts:register")


def test_duplicate_email_stays_on_form_without_second_account_or_mail(client):
    client.post(reverse("accounts:register"), registration_data())
    response = client.post(
        reverse("accounts:register"), registration_data("NEW.MEMBER@EXAMPLE.COM")
    )
    assert response.status_code == 200
    assert "An account with this email already exists." in response.text
    assert get_user_model().objects.count() == 1
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("password", ["short", "123456789012", "password"])
def test_invalid_password_stays_on_form(client, password):
    response = client.post(reverse("accounts:register"), registration_data(password=password))
    assert response.status_code == 200
    assert response.context["form"].errors
    assert not get_user_model().objects.exists()
    assert not mail.outbox


def test_race_integrity_error_keeps_friendly_form_error(client):
    # Exercise the existing race handler deterministically; not a concurrency test.
    with patch("accounts.forms.RegistrationForm.save", side_effect=IntegrityError):
        response = client.post(reverse("accounts:register"), registration_data())
    assert response.status_code == 200
    assert "An account with this email already exists." in response.text
    assert not get_user_model().objects.exists()
    assert not mail.outbox


def test_mail_failure_does_not_prevent_redirect_or_account_creation(client):
    with patch("notif.services.send_mail", side_effect=OSError("test mail outage")):
        response = client.post(reverse("accounts:register"), registration_data())
    assert response.status_code == 302
    assert response.url == reverse("accounts:registration_success")
    assert get_user_model().objects.count() == 1
    assert "new.member@example.com" in client.get(response.url).text


def test_registration_still_enforces_csrf():
    from django.test import Client

    response = Client(enforce_csrf_checks=True).post(
        reverse("accounts:register"), registration_data()
    )
    assert response.status_code == 403
    assert not get_user_model().objects.exists()

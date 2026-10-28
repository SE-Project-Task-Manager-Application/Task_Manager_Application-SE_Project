"""User model rules that other stories rely on (S-02 review follow-ups)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


def test_superuser_defaults_to_admin_role():
    user = get_user_model().objects.create_superuser(email="root@example.com", password="x")
    assert user.role == "admin"
    assert user.is_staff and user.is_superuser


def test_new_user_defaults_to_member():
    user = get_user_model().objects.create_user(email="m@example.com", password="x")
    assert user.role == "member"


def test_email_is_lowercased_completely():
    user = get_user_model().objects.create_user(email="Mixed.Case@EXAMPLE.com", password="x")
    assert user.email == "mixed.case@example.com"


def test_emails_differing_only_in_case_cannot_both_register():
    model = get_user_model()
    model.objects.create_user(email="a@example.com", password="x")
    with pytest.raises(IntegrityError), transaction.atomic():
        model.objects.create_user(email="A@Example.COM", password="x")

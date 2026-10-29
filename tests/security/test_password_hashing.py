"""TM-SR-002: passwords are stored with salted Argon2 hashing, never plaintext (TC-Sec-02)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import override_settings

from config.settings import base

pytestmark = pytest.mark.django_db

PASSWORD = "S3cure-Passw0rd!"


def test_argon2_is_the_first_configured_hasher():
    assert base.PASSWORD_HASHERS[0] == "django.contrib.auth.hashers.Argon2PasswordHasher"


@override_settings(PASSWORD_HASHERS=base.PASSWORD_HASHERS)
def test_password_is_stored_as_salted_argon2_hash():
    user = get_user_model().objects.create_user(email="hash@example.com", password=PASSWORD)
    user.refresh_from_db()
    assert user.password.startswith("argon2$")
    assert PASSWORD not in user.password
    assert user.check_password(PASSWORD)


@override_settings(PASSWORD_HASHERS=base.PASSWORD_HASHERS)
def test_same_password_gets_different_salts():
    first = get_user_model().objects.create_user(email="a@example.com", password=PASSWORD)
    second = get_user_model().objects.create_user(email="b@example.com", password=PASSWORD)
    assert first.password != second.password


@override_settings(PASSWORD_HASHERS=base.PASSWORD_HASHERS)
def test_legacy_pbkdf2_hash_still_verifies_and_upgrades_to_argon2():
    user = get_user_model().objects.create_user(email="old@example.com", password="x")
    user.password = make_password(
        PASSWORD, hasher="pbkdf2_sha256"
    )
    user.save()
    assert user.password.startswith("pbkdf2_sha256$")
    assert user.check_password(PASSWORD)  # verifies, and re-hashes on success
    user.refresh_from_db()
    assert user.password.startswith("argon2$")

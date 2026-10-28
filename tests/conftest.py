"""Shared pytest fixtures for the whole suite."""

import itertools

import pytest
from django.contrib.auth import get_user_model

TEST_PASSWORD = "SEPROG123"  # same test-only password as SETUP.md


@pytest.fixture
def make_user(db):
    """Create a user with the given role. Adapt here if the User manager changes."""
    counter = itertools.count(1)

    def _make(role="member", email=None, **extra):
        user_model = get_user_model()
        email = email or f"user{next(counter)}@example.com"
        user = user_model.objects.create_user(email=email, password=TEST_PASSWORD, **extra)
        if user.role != role:
            user.role = role
            user.save(update_fields=["role"])
        return user

    return _make

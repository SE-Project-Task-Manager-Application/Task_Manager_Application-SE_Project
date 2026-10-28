"""S-03: the shared form component renders accessible, labelled, validated fields."""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def form_html(client, make_user):
    client.force_login(make_user())
    return client.post(reverse("tasks:create"), {"title": "", "priority": "low"}).content.decode()


def test_every_text_input_has_a_matching_label(form_html):
    for field_id in re.findall(r'<(?:input|select|textarea)[^>]* id="(id_[a-z_]+)"', form_html):
        if field_id.startswith(("id_labels", "id_assignees")):
            continue  # checkbox groups are labelled by their fieldset legend
        assert f'<label for="{field_id}">' in form_html


def test_invalid_field_is_flagged_and_linked_to_its_error(form_html):
    assert 'aria-invalid="true"' in form_html
    assert 'aria-describedby="id_title_error"' in form_html
    assert 'id="id_title_error"' in form_html


def test_error_summary_is_announced(form_html):
    assert 'class="error-summary" role="alert"' in form_html


def test_required_fields_are_marked(form_html):
    assert 'class="field field--required"' in form_html

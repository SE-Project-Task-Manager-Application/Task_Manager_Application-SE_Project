from django.urls import reverse

GENERIC_ERROR = b"We couldn't log you in. Check your email and password and try again."
PASSWORD = "SEPROG123"


def _visible_error(response):
    marker = b'<p class="error-summary__title">'
    start = response.content.index(marker) + len(marker)
    end = response.content.index(b"</p>", start)
    return b" ".join(response.content[start:end].split())


def test_tc_auth_02_login_and_generic_failures(client, make_user):
    user = make_user(email="valid@example.com")
    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": PASSWORD},
    )

    assert response.status_code == 302
    assert response.url == reverse("tasks:list")
    assert client.session["_auth_user_id"] == str(user.pk)

    inactive_user = make_user(email="inactive@example.com")
    inactive_user.is_active = False
    inactive_user.save(update_fields=["is_active"])

    attempts = [
        {"username": user.email, "password": "wrong-password"},
        {"username": "unknown@example.com", "password": PASSWORD},
        {"username": inactive_user.email, "password": PASSWORD},
    ]
    errors = []

    for credentials in attempts:
        client.logout()
        response = client.post(reverse("accounts:login"), credentials)

        assert response.status_code == 200
        errors.append(_visible_error(response))
        assert "_auth_user_id" not in client.session

    assert errors == [GENERIC_ERROR, GENERIC_ERROR, GENERIC_ERROR]
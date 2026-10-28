"""S-03: base layout, role-aware navigation and accessibility baseline."""

import re
import sys
import types
from types import SimpleNamespace

import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import include, path

from config.context_processors import navigation


def _stub_view(request):
    return HttpResponse("ok")


@pytest.fixture
def nav_urls(settings):
    """A throw-away URLconf that defines the URL names the menu looks for."""
    module = types.ModuleType("nav_test_urls")
    module.urlpatterns = [
        path("tasks/", include(([path("", _stub_view, name="list"),
                                 path("new/", _stub_view, name="create")], "tasks"))),
        path("dash/", include(([path("", _stub_view, name="index")], "dash"))),
        path("manage/", include(([path("", _stub_view, name="index")], "adminpanel"))),
        path("acct/", include(([path("login/", _stub_view, name="login"),
                                path("logout/", _stub_view, name="logout")], "accounts"))),
    ]
    sys.modules["nav_test_urls"] = module
    settings.ROOT_URLCONF = "nav_test_urls"
    yield module
    del sys.modules["nav_test_urls"]


def _items(role, path_="/"):
    request = RequestFactory().get(path_)
    request.user = SimpleNamespace(is_authenticated=True, role=role)
    return navigation(request)["nav_items"]


def _labels(role):
    return [item["label"] for item in _items(role)]


def test_home_page_has_accessibility_landmarks(client):
    html = client.get("/").content.decode()
    assert '<html lang="en">' in html
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in html
    assert '<a class="skip-link" href="#main">' in html
    assert '<main id="main"' in html
    assert '<nav aria-label="Main">' in html
    assert len(re.findall(r"<h1[ >]", html)) == 1


def test_member_sees_member_menu(nav_urls):
    assert _labels("member") == ["Tasks", "New task", "Dashboard", "Log out"]


def test_project_manager_sees_same_menu_as_member(nav_urls):
    assert _labels("project_manager") == ["Tasks", "New task", "Dashboard", "Log out"]


def test_only_admin_sees_administration(nav_urls):
    assert "Administration" in _labels("admin")
    assert "Administration" not in _labels("member")
    assert "Administration" not in _labels("project_manager")


def test_guest_sees_only_login(nav_urls):
    request = RequestFactory().get("/")
    request.user = SimpleNamespace(is_authenticated=False)
    labels = [item["label"] for item in navigation(request)["nav_items"]]
    assert labels == ["Log in"]  # "Register" is skipped: no such URL name yet


def test_menu_skips_entries_whose_pages_do_not_exist():
    # Without the stub URLconf, none of the optional menu URL names exist.
    assert [i for i in _items("admin") if i["label"] == "Administration"] == []


def test_current_page_is_marked(nav_urls):
    items = _items("member", "/tasks/")
    assert [i["label"] for i in items if i["current"]] == ["Tasks"]


def test_logout_is_a_post_button(nav_urls):
    items = {i["label"]: i for i in _items("member")}
    assert items["Log out"]["post"] is True
    assert items["Tasks"]["post"] is False

"""Template context shared by every page: the role-aware main navigation (S-03).

Navigation entries are declared once, here, with the roles that may see them.
An entry whose URL name does not exist yet is skipped, so later stories (dashboard,
administration, login) appear in the menu as soon as they register their URLs, with
no template change.
"""

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse

MEMBER = "member"
PROJECT_MANAGER = "project_manager"
ADMIN = "admin"
ALL_ROLES = (MEMBER, PROJECT_MANAGER, ADMIN)


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    roles: tuple = ALL_ROLES
    post: bool = False  # rendered as a POST button (Django's logout requires POST)


# Shown to logged-in users, filtered by role.
USER_NAV = (
    NavItem("Tasks", "tasks:list"),
    NavItem("New task", "tasks:create"),
    NavItem("Dashboard", "dash:index"),
    NavItem("Administration", "adminpanel:index", roles=(ADMIN,)),
    NavItem("Log out", "accounts:logout", post=True),
)

# Shown to guests (not logged in).
GUEST_NAV = (
    NavItem("Log in", "accounts:login", roles=()),
    NavItem("Register", "accounts:register", roles=()),
)


def _resolve(items, request, role):
    current_path = request.path
    resolved = []
    for item in items:
        if item.roles and role not in item.roles:
            continue
        try:
            url = reverse(item.url_name)
        except NoReverseMatch:
            continue
        resolved.append(
            {
                "label": item.label,
                "url": url,
                "post": item.post,
                "current": url == current_path,
            }
        )
    return resolved


def navigation(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        role = getattr(user, "role", MEMBER) or MEMBER
        return {"nav_items": _resolve(USER_NAV, request, role), "nav_role": role}
    return {"nav_items": _resolve(GUEST_NAV, request, None), "nav_role": None}

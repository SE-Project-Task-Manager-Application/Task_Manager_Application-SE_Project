from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import LockoutAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="accounts/login.html",
            redirect_authenticated_user=True,
            authentication_form=LockoutAuthenticationForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="home"),
        name="logout",
    ),
    path("password-reset/", views.PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("profile/", views.profile, name="profile"),
    path("profile/avatar/", views.avatar, name="avatar"),
    path(
        "profile/password/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("accounts:profile"),
        ),
        name="password_change",
    ),
    path("profile/email/confirm/<token>/", views.confirm_email_change, name="email_confirm"),
    path("register/", views.register, name="register"),
    path(
        "register/success/",
        views.registration_success,
        name="registration_success",
    ),
]
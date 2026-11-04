from django.contrib.auth import views as auth_views
from django.urls import path

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
    path("register/", views.register, name="register"),
    path(
        "register/success/",
        views.registration_success,
        name="registration_success",
    ),
]
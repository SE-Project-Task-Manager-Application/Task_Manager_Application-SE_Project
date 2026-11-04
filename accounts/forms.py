from datetime import timedelta

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from adminpanel.services import AuditService

from .models import User


class RegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


class LockoutAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": (
            "We couldn't log you in. Check your email and password and try again."
        ),
    }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if not username or not password:
            return self.cleaned_data

        invalid_login = False

        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(email__iexact=username)
                .first()
            )
            now = timezone.now()

            if user and user.locked_until and user.locked_until > now:
                # Keep the current lock expiry; don't count attempts made while locked.
                invalid_login = True
            else:
                if user and user.locked_until:
                    # The previous lock expired. Start a fresh attempt count.
                    user.failed_login_attempts = 0
                    user.locked_until = None
                    user.save(
                        update_fields=["failed_login_attempts", "locked_until"]
                    )

                authenticated_user = authenticate(
                    self.request,
                    username=user.email if user else username,
                    password=password,
                )

                if authenticated_user is None:
                    invalid_login = True

                    if user and user.is_active:
                        user.failed_login_attempts += 1
                        fields_to_update = ["failed_login_attempts"]

                        if user.failed_login_attempts == 5:
                            user.locked_until = now + timedelta(minutes=15)
                            fields_to_update.append("locked_until")

                            AuditService.record(
                                actor=None,
                                action="auth.account_locked",
                                target=user,
                                details={"failed_login_attempts": 5},
                            )

                        user.save(update_fields=fields_to_update)
                else:
                    authenticated_user.failed_login_attempts = 0
                    authenticated_user.locked_until = None
                    authenticated_user.save(
                        update_fields=["failed_login_attempts", "locked_until"]
                    )
                    self.user_cache = authenticated_user
                    self.confirm_login_allowed(authenticated_user)
                    return self.cleaned_data

        # Raise after leaving atomic so the failed-attempt update and audit commit.
        if invalid_login:
            raise ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
            )

        return self.cleaned_data
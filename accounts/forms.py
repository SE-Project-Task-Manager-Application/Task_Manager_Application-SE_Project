from datetime import timedelta

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template import loader
from django.utils import timezone

from adminpanel.services import AuditService
from notif.services import NotificationEvent, NotificationService

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
AVATAR_TYPES = (".png", ".jpg", ".jpeg", ".gif")
AVATAR_SIGNATURES = (  # first bytes of the file -> the extensions that may carry them
    (b"\x89PNG\r\n\x1a\n", (".png",)),
    (b"\xff\xd8\xff", (".jpg", ".jpeg")),
    (b"GIF87a", (".gif",)),
    (b"GIF89a", (".gif",)),
)
AVATAR_MAX_BYTES = 10 * 1024 * 1024  # 10 MB, same limit as attachments (SAD)


class ResetRequestForm(PasswordResetForm):
    """Password reset request that sends its e-mail through NotificationService."""

    def get_users(self, email):
        # Skip inactive and soft-deleted accounts. Django already skips unusable passwords.
        return (
            u
            for u in super().get_users(email)
            if u.deleted_at is None
        )

    def send_mail(
        self, subject_template_name, email_template_name, context, from_email,
        to_email, html_email_template_name=None,
    ):
        subject = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        body = loader.render_to_string(email_template_name, context)
        recipient = type("Recipient", (), {"email": to_email, "pk": context["user"].pk})()
        NotificationService.send(
            NotificationEvent(
                kind="account.password_reset",
                recipient=recipient,
                subject=subject,
                body=body,
            )
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "avatar")

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        # An existing saved file is not re-checked; only a new upload has a size.
        if avatar and hasattr(avatar, "size") and hasattr(avatar, "content_type"):
            if not avatar.name.lower().endswith(AVATAR_TYPES):
                raise forms.ValidationError("Use a PNG, JPG or GIF image.")
            if avatar.size > AVATAR_MAX_BYTES:
                raise forms.ValidationError("The image must be 10 MB or smaller.")
            # The extension is only a label: check the file's first bytes too.
            head = avatar.read(8)
            avatar.seek(0)
            extension = "." + avatar.name.lower().rsplit(".", 1)[-1]
            if not any(
                head.startswith(sig) and extension in exts for sig, exts in AVATAR_SIGNATURES
            ):
                raise forms.ValidationError("That file is not a valid PNG, JPG or GIF image.")
        return avatar


class EmailChangeForm(forms.Form):
    new_email = forms.EmailField()

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_new_email(self):
        email = self.cleaned_data["new_email"].strip().lower()
        if email == self.user.email:
            raise forms.ValidationError("That is already your email address.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

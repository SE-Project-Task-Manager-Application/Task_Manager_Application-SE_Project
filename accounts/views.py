from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import FileResponse, Http404
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_GET

from notif.services import NotificationEvent, NotificationService

from .forms import EmailChangeForm, ProfileForm, RegistrationForm, ResetRequestForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
            except IntegrityError:
                form.add_error(
                    "email",
                    "An account with this email already exists.",
                )
            else:
                event = NotificationEvent(
                    kind="account.created",
                    recipient=user,
                    subject="Task Manager account confirmation",
                    body=(
                        f"Your Task Manager account has been created "
                        f"for {user.email}."
                    ),
                )
                NotificationService.send(event)

                # Keep personal data out of the URL and render success through GET.
                request.session["registration_email"] = user.email
                return redirect("accounts:registration_success")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@require_GET
def registration_success(request):
    email = request.session.get("registration_email")
    if not email:
        return redirect("accounts:register")
    return render(request, "accounts/registration_success.html", {"email": email})


# ---- Password reset (TM-F-004) and profile (TM-F-005) ----

EMAIL_CHANGE_SALT = "accounts.email-change"
EMAIL_CHANGE_MAX_AGE = 24 * 60 * 60  # the confirmation link lasts 24 hours


class PasswordResetRequestView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = ResetRequestForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


@login_required
def profile(request):
    profile_form = ProfileForm(instance=request.user)
    email_form = EmailChangeForm(user=request.user)

    if request.method == "POST":
        if "save_profile" in request.POST:
            profile_form = ProfileForm(request.POST, request.FILES, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile has been saved.")
                return redirect("accounts:profile")
        else:
            email_form = EmailChangeForm(request.POST, user=request.user)
            if email_form.is_valid():
                new_email = email_form.cleaned_data["new_email"]
                token = signing.dumps(
                    {"uid": request.user.pk, "old": request.user.email, "new": new_email},
                    salt=EMAIL_CHANGE_SALT,
                )
                link = request.build_absolute_uri(
                    reverse("accounts:email_confirm", args=[token])
                )
                recipient = type("Recipient", (), {"email": new_email, "pk": request.user.pk})()
                sent = NotificationService.send(
                    NotificationEvent(
                        kind="account.email_change",
                        recipient=recipient,
                        subject="Confirm your new Task Manager email",
                        body=(
                            "Open this link to confirm your new email address. "
                            f"It works for 24 hours:\n\n{link}\n\n"
                            "If you did not ask for this, ignore this message."
                        ),
                    )
                )
                if sent:
                    messages.success(
                        request,
                        f"We sent a confirmation link to {new_email}. "
                        "Your email will change after you open it.",
                    )
                else:
                    messages.error(
                        request,
                        "We could not send the confirmation email. "
                        "Your email was not changed. Please try again later.",
                    )
                return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {"profile_form": profile_form, "email_form": email_form},
    )


@login_required
def confirm_email_change(request, token):
    try:
        data = signing.loads(token, salt=EMAIL_CHANGE_SALT, max_age=EMAIL_CHANGE_MAX_AGE)
    except signing.BadSignature:
        messages.error(request, "That confirmation link is invalid or has expired.")
        return redirect("accounts:profile")

    user = request.user
    # The link only works for the user who asked, and only while the old email is current.
    if data["uid"] != user.pk or data["old"] != user.email:
        messages.error(request, "That confirmation link is invalid or has expired.")
        return redirect("accounts:profile")

    user.email = data["new"]
    try:
        with transaction.atomic():
            user.save(update_fields=["email"])
    except IntegrityError:
        messages.error(request, "An account with that email already exists.")
    else:
        messages.success(request, "Your email address has been updated.")
    return redirect("accounts:profile")


@login_required
def avatar(request):
    """Serve the logged-in user's own profile picture (works in production too)."""
    if not request.user.avatar:
        raise Http404
    try:
        return FileResponse(request.user.avatar.open("rb"))
    except FileNotFoundError:
        raise Http404 from None

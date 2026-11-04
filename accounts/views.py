from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from notif.services import NotificationEvent, NotificationService

from .forms import RegistrationForm


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

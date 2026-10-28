from django.shortcuts import render

from notif.services import NotificationEvent, NotificationService

from .forms import RegistrationForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

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

            return render(
                request,
                "accounts/registration_success.html",
                {"email": user.email},
            )
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
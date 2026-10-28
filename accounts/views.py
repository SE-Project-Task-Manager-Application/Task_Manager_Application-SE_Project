from django.shortcuts import render

from notif.services import NotificationService

from .forms import RegistrationForm


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()

            NotificationService.enqueue(
                recipient=user.email,
                subject="Task Manager account confirmation",
                message=(
                    f"Your Task Manager account has been created "
                    f"for {user.email}."
                ),
            )

            return render(
                request,
                "accounts/registration_success.html",
                {"email": user.email},
            )
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})
# Create your views here.

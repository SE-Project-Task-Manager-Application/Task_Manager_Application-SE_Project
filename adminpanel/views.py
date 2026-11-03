from functools import wraps

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .services import AuditService


User = get_user_model()


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            return HttpResponseForbidden("Administrator access required.")
        return view(request, *args, **kwargs)

    return wrapped


@require_GET
@admin_required
def user_list(request):
    users = User.objects.filter(deleted_at__isnull=True).order_by("email")
    return render(request, "adminpanel/user_list.html", {"users": users})


@require_POST
@admin_required
def disable_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.pk == request.user.pk:
        return HttpResponseForbidden("You cannot disable your own account.")

    if user.is_active:
        with transaction.atomic():
            user.is_active = False
            user.save(update_fields=["is_active"])
            AuditService.record(
                actor=request.user,
                action="user.disabled",
                target=("user", user.pk),
                details={"email": user.email},
            )

    return redirect("adminpanel:user_list")


@require_POST
@admin_required
def enable_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.is_active:
        return redirect("adminpanel:user_list")

    with transaction.atomic():
        user.is_active = True
        user.save(update_fields=["is_active"])
        AuditService.record(
            actor=request.user,
            action="user.enabled",
            target=("user", user.pk),
            details={"email": user.email},
        )

    return redirect("adminpanel:user_list")


@require_POST
@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.pk == request.user.pk:
        return HttpResponseForbidden("You cannot delete your own account.")

    with transaction.atomic():
        AuditService.record(
            actor=request.user,
            action="user.deleted",
            target=("user", user.pk),
            details={"email": user.email},
        )
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(update_fields=["is_active", "deleted_at"])

    return redirect("adminpanel:user_list")

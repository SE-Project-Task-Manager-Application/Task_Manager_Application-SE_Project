from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import AuditRecord
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


@require_GET
@admin_required
def audit_log(request):
    query = request.GET.get("q", "").strip()[:100]
    records = AuditRecord.objects.select_related("actor").all()
    if query:
        records = records.filter(
            Q(actor__email__icontains=query)
            | Q(action__icontains=query)
            | Q(target_type__icontains=query)
            | Q(target_id__icontains=query)
        )

    page_obj = Paginator(records, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "adminpanel/audit_log.html",
        {"page_obj": page_obj, "query": query},
    )


@require_POST
@admin_required
def disable_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.pk == request.user.pk:
        messages.error(request, "You cannot disable your own account.")
        return redirect("adminpanel:user_list")

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

    messages.success(request, f"{user.email} has been disabled.")
    return redirect("adminpanel:user_list")


@require_POST
@admin_required
def enable_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.is_active:
        messages.success(request, f"{user.email} is already enabled.")
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

    messages.success(request, f"{user.email} has been enabled.")
    return redirect("adminpanel:user_list")


@require_POST
@admin_required
def delete_user(request, user_id):
    user = get_object_or_404(
        User, pk=user_id, deleted_at__isnull=True
    )
    if user.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("adminpanel:user_list")

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

    messages.success(request, f"{user.email} has been deleted.")
    return redirect("adminpanel:user_list")

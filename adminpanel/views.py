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
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from tasks.models import Label

from .forms import LabelForm
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


@require_http_methods(["GET", "POST"])
@admin_required
def category_list(request):
    """TM-F-051: list all categories and add a new one."""
    if request.method == "POST":
        form = LabelForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                label = form.save()
                AuditService.record(
                    actor=request.user,
                    action="label.created",
                    target=label,
                    details={"name": label.name},
                )
            messages.success(request, f"Category '{label.name}' created.")
            return redirect("adminpanel:category_list")
    else:
        form = LabelForm()
    return render(
        request,
        "adminpanel/category_list.html",
        {"labels": Label.objects.all(), "form": form},
    )


@require_http_methods(["GET", "POST"])
@admin_required
def category_rename(request, label_id):
    label = get_object_or_404(Label, pk=label_id)
    old_name = label.name
    if request.method == "POST":
        form = LabelForm(request.POST, instance=label)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                if label.name != old_name:
                    AuditService.record(
                        actor=request.user,
                        action="label.renamed",
                        target=label,
                        details={"old_name": old_name, "new_name": label.name},
                    )
            messages.success(request, f"Category renamed to '{label.name}'.")
            return redirect("adminpanel:category_list")
    else:
        form = LabelForm(instance=label)
    return render(
        request,
        "adminpanel/category_form.html",
        {"form": form, "current_name": old_name},
    )


def _set_archived(request, label_id, archived):
    label = get_object_or_404(Label, pk=label_id)
    state = "archived" if archived else "active"
    if label.is_archived == archived:
        messages.success(request, f"'{label.name}' is already {state}.")
        return redirect("adminpanel:category_list")

    with transaction.atomic():
        label.is_archived = archived
        label.save(update_fields=["is_archived"])
        AuditService.record(
            actor=request.user,
            action="label.archived" if archived else "label.restored",
            target=label,
            details={"name": label.name},
        )
    messages.success(request, f"'{label.name}' is now {state}.")
    return redirect("adminpanel:category_list")


@require_POST
@admin_required
def category_archive(request, label_id):
    return _set_archived(request, label_id, True)


@require_POST
@admin_required
def category_restore(request, label_id):
    return _set_archived(request, label_id, False)

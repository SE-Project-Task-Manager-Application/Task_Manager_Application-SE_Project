
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.views.decorators.http import require_GET, require_POST

from accounts.services import require_task_permission
from tasks.models import Task
from adminpanel.services import AuditService

from .forms import AttachmentForm
from .models import TaskAttachment


@login_required
@require_POST
def upload_attachment(request, task_id):
    task = get_object_or_404(Task.objects.active(), pk=task_id)
    require_task_permission(request.user, task, "edit")
    form = AttachmentForm(request.POST, request.FILES)
    if form.is_valid():
        upload = form.cleaned_data["file"]
        with transaction.atomic():
            attachment = TaskAttachment.objects.create(
                task=task,
                uploaded_by=request.user,
                file=upload,
                original_name=upload.name,
                size=upload.size,
                content_type=getattr(upload, "content_type", "")[:100],
            )
            AuditService.record(
                actor=request.user,
                action="task.attachment_added",
                target=task,
                details={"attachment_id": attachment.pk, "filename": attachment.original_name},
            )
        messages.success(request, "Attachment uploaded.")
    else:
        for error in form.errors.get("file", ["The attachment could not be uploaded."]):
            messages.error(request, error)
    return redirect("tasks:list")


@login_required
@require_GET
def download_attachment(request, attachment_id):
    attachment = get_object_or_404(
        TaskAttachment.objects.select_related("task"),
        pk=attachment_id,
        task__deleted_at__isnull=True,
    )
    require_task_permission(request.user, attachment.task, "view")
    try:
        response = FileResponse(
            attachment.file.open("rb"),
            as_attachment=True,
            filename=attachment.original_name,
        )
    except FileNotFoundError:
        raise Http404 from None
    response["X-Content-Type-Options"] = "nosniff"
    return response

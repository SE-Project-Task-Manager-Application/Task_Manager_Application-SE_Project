from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tasks.models import Task

from .forms import TaskShareForm
from .services import TaskShareService
from .models import TaskShare


class TaskShareView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        # Use the same visibility scope as the task list to avoid revealing whether
        # another user's task ID exists. Visible non-owners still receive 403.
        task = get_object_or_404(Task.objects.active().visible_to(request.user), pk=task_id)
        if task.owner_id != request.user.pk:
            return HttpResponseForbidden("Only the task owner can share this task.")

        form = TaskShareForm(request.POST)
        if not form.is_valid():
            messages.error(request, " ".join(
                error for errors in form.errors.values() for error in errors
            ))
            return redirect("tasks:list")
        try:
            TaskShareService.share(
                task, form.user, form.cleaned_data["permission"], request.user
            )
        except PermissionDenied:
            return HttpResponseForbidden("Only an active task owner can share this task.")
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return redirect("tasks:list")

        messages.success(
            request,
            f"Task shared with {form.user.email} as {form.cleaned_data['permission']}.",
        )
        return redirect("tasks:list")


class TaskShareRevokeView(LoginRequiredMixin, View):
    def post(self, request, task_id, share_id):
        # Keep deleted tasks in scope so owners can revoke access at any time.
        task = get_object_or_404(Task.objects.filter(owner=request.user), pk=task_id)
        share = get_object_or_404(TaskShare, pk=share_id, task=task)
        try:
            revoked = TaskShareService.revoke(task, share.user, request.user)
        except PermissionDenied:
            return HttpResponseForbidden("Only an active task owner can revoke task access.")

        if revoked:
            messages.success(request, f"Access revoked for {share.user.email}.")
        else:
            messages.info(request, "That collaborator no longer has access.")
        return redirect("tasks:list")

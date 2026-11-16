from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tasks.models import Task

from .forms import CommentForm, TaskShareForm
from .models import TaskShare
from .services import ActivityService, CommentService, TaskShareService


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


class TaskCommentsView(LoginRequiredMixin, View):
    """Show a task's comments and let anyone with access add one (TM-F-033).

    A user without access gets 403 (SAD 4.4); a missing or deleted task gets 404.
    """

    template_name = "collab/task_comments.html"

    def _task(self):
        return get_object_or_404(Task.objects.active(), pk=self.kwargs["pk"])

    def _render(self, request, task, form, status=200):
        context = {
            "task": task,
            "comments": CommentService.for_task(request.user, task),
            "form": form,
        }
        return render(request, self.template_name, context, status=status)

    def get(self, request, pk):
        return self._render(request, self._task(), CommentForm())

    def post(self, request, pk):
        task = self._task()
        form = CommentForm(request.POST)
        if form.is_valid():
            try:
                CommentService.add(request.user, task, form.cleaned_data["body"])
            except ValidationError as error:
                form.add_error(None, error.messages[0])
            else:
                messages.success(request, "Comment added.")
                return redirect("collab:task_comments", pk=task.pk)
        return self._render(request, task, form, status=400)


class TaskActivityView(LoginRequiredMixin, View):
    """Chronological activity history for a task (TM-F-034).

    Anyone who can view the task sees its history, including after it is deleted, so
    the deletion itself is visible. A user without access gets 403 (SAD 4.4).
    """

    template_name = "collab/task_activity.html"

    def get(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        entries = ActivityService.for_task(request.user, task)
        return render(request, self.template_name, {"task": task, "entries": entries})

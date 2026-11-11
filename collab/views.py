from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tasks.models import Task

from .forms import CommentForm
from .services import CommentService


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

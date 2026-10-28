from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.views.generic import FormView, ListView

from .forms import TaskCreateForm
from .models import Task
from .services import TaskService


class TaskListView(LoginRequiredMixin, ListView):
    """Tasks the user owns or is assigned to (sharing is added by the collab stories)."""

    template_name = "tasks/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        user = self.request.user
        return (
            Task.objects.active()
            .filter(Q(owner=user) | Q(assignments__user=user))
            .select_related("owner")
            .prefetch_related("labels", "assignees")
            .distinct()
        )


class TaskCreateView(LoginRequiredMixin, FormView):
    template_name = "tasks/task_form.html"
    form_class = TaskCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        data = form.cleaned_data
        TaskService.create(
            self.request.user,
            title=data["title"],
            description=data["description"],
            due_date=data["due_date"],
            priority=data["priority"],
            labels=data["labels"],
            assignees=data.get("assignees", []),
        )
        messages.success(self.request, "Task created.")
        return redirect("tasks:list")

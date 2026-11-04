from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import FormView, ListView, UpdateView

from accounts.services import require_task_permission

from .forms import TaskCreateForm, TaskForm
from .models import Task
from .services import StaleTaskError, TaskService


class TaskListView(LoginRequiredMixin, ListView):
    """Tasks the user owns or is assigned to (sharing is added by the collab stories)."""

    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20
    task_status_choices = Task.Status.choices
    task_priority_choices = Task.Priority.choices

    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.active()
        if getattr(user, "role", None) != "admin":
            queryset = queryset.filter(Q(owner=user) | Q(assignments__user=user))
        queryset = (
            queryset.select_related("owner").prefetch_related("labels", "assignees").distinct()
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(Q(title__icontains=query) | Q(description__icontains=query))
        for field in ("priority", "status"):
            value = self.request.GET.get(field)
            if value in dict(getattr(Task, field.title()).choices):
                queryset = queryset.filter(**{field: value})
        label = self.request.GET.get("label")
        if label:
            queryset = queryset.filter(labels__name__iexact=label)
        due_date = self.request.GET.get("due_date")
        if due_date:
            queryset = queryset.filter(due_date__date=due_date)
        if self.request.GET.get("show") != "all":
            queryset = queryset.exclude(status=Task.Status.DONE)
        sort_fields = {"title", "priority", "status", "due_date", "created_at", "updated_at"}
        sort = self.request.GET.get("sort", "created_at")
        if sort not in sort_fields:
            sort = "created_at"
        if self.request.GET.get("direction") == "asc":
            queryset = queryset.order_by(sort, "id")
        else:
            queryset = queryset.order_by(f"-{sort}", "-id")
        return queryset


class TaskEditView(LoginRequiredMixin, UpdateView):
    template_name = "tasks/task_form.html"
    form_class = TaskForm
    context_object_name = "task"

    def get_object(self, queryset=None):
        task = get_object_or_404(Task, pk=self.kwargs["pk"])
        require_task_permission(self.request.user, task, "edit")
        return task

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["include_status"] = True
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["expected_version"] = self.object.version
        initial["assignees"] = self.object.assignees.values_list("pk", flat=True)
        return initial

    def form_valid(self, form):
        changes = {
            field: form.cleaned_data[field]
            for field in ("title", "description", "due_date", "priority", "status", "labels")
            if field in form.cleaned_data
        }
        if "assignees" in form.cleaned_data:
            changes["assignees"] = form.cleaned_data["assignees"]
        try:
            TaskService.update(
                self.request.user,
                self.object,
                expected_version=form.cleaned_data.get("expected_version"),
                **changes,
            )
        except (ValidationError, StaleTaskError) as error:
            form.add_error(None, error.messages[0])
            return self.form_invalid(form)
        messages.success(self.request, "Task updated.")
        return redirect("tasks:list")


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


def _task_action(request, pk, action, success_message):
    task = get_object_or_404(Task, pk=pk)
    if action == "delete":
        TaskService.delete(request.user, task, request.POST.get("expected_version"))
    elif action == "restore":
        TaskService.restore(request.user, task, request.POST.get("expected_version"))
    else:
        TaskService.set_status(request.user, task, action, request.POST.get("expected_version"))
    messages.success(request, success_message)
    return redirect("tasks:list")


@require_POST
def delete_task(request, pk):
    return _task_action(request, pk, "delete", "Task deleted.")


@require_POST
def restore_task(request, pk):
    return _task_action(request, pk, "restore", "Task restored.")


@require_POST
def complete_task(request, pk):
    return _task_action(request, pk, Task.Status.DONE, "Task completed.")


@require_POST
def reopen_task(request, pk):
    return _task_action(request, pk, Task.Status.TODO, "Task reopened.")

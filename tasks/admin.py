from django.contrib import admin

from .models import Label, Task, TaskAssignment


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    fk_name = "task"
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "priority", "due_date", "deleted_at")
    list_filter = ("status", "priority")
    search_fields = ("title",)
    inlines = [TaskAssignmentInline]


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived")
    list_filter = ("is_archived",)


from django.contrib import admin

from .models import TaskShare


@admin.register(TaskShare)
class TaskShareAdmin(admin.ModelAdmin):
    list_display = ("task", "user", "permission", "shared_by", "shared_at")
    list_filter = ("permission",)
    search_fields = ("task__title", "user__email", "shared_by__email")

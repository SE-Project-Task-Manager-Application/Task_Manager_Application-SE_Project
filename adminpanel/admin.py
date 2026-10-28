from django.contrib import admin

from .models import AuditRecord


@admin.register(AuditRecord)
class AuditRecordAdmin(admin.ModelAdmin):
    """Read-only view of the audit log: nobody can add, edit or delete rows here."""

    list_display = ("created_at", "actor", "action", "target_type", "target_id")
    list_filter = ("action", "target_type")
    search_fields = ("action", "target_id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

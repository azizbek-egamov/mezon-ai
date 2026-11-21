from django.contrib import admin

from .models import SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ["started_at", "finished_at", "status", "new_count", "refreshed_count", "error_count"]
    list_filter = ["status"]
    readonly_fields = ["started_at", "finished_at", "status", "stats", "log"]

    @admin.display(description="yangi hujjatlar")
    def new_count(self, run):
        return len(run.stats.get("new_documents", []))

    @admin.display(description="qayta yuklangan")
    def refreshed_count(self, run):
        return len(run.stats.get("refreshed", []))

    @admin.display(description="xatolar")
    def error_count(self, run):
        return len(run.stats.get("errors", []))

    def has_add_permission(self, request):
        return False

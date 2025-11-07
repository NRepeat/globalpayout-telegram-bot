from django.contrib import admin

from api.models import AllowedApi, ApiReqLog


@admin.register(AllowedApi)
class AllowedApiAdmin(admin.ModelAdmin):
    list_display = (
        "record_id",
        "api_key",
        "comment",
    )


@admin.register(ApiReqLog)
class ApiReqLogAdmin(admin.ModelAdmin):
    list_display = ("record_id", "headers", "body", "ip_address", "date")
    readonly_fields = ("record_id", "headers", "body", "ip_address", "date")

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

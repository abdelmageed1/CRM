from django.contrib import admin
from .models import ClientEditRequest

@admin.register(ClientEditRequest)
class ClientEditRequestAdmin(admin.ModelAdmin):
    list_display = ('requested_by', 'client_name', 'client_id', 'status', 'created_at', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('requested_by__username', 'client_name', 'reason')
    readonly_fields = ('requested_by', 'client_id', 'client_name', 'old_data', 'new_data', 'created_at', 'reviewed_at')
    ordering = ('-created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('requested_by', 'reviewed_by')


from django.contrib import admin

from .models import ClientProfile


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'profile_type', 'active', 'start_date')
    list_filter = ('profile_type', 'active')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user',)

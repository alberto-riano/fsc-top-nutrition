from django.contrib import admin

from .models import Plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'plan_type', 'archived', 'date')
    list_filter = ('plan_type', 'archived')
    search_fields = ('title', 'client__user__first_name', 'client__user__last_name')

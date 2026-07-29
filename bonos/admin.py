from django.contrib import admin

from .models import Bono, Session


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0


@admin.register(Bono)
class BonoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'client', 'bono_type', 'sessions_total', 'status', 'purchase_date')
    list_filter = ('bono_type', 'archived')
    search_fields = ('client__user__first_name', 'client__user__last_name')
    inlines = [SessionInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'bono', 'date')
    list_filter = ('session_type',)

from django.contrib import admin

from .models import Plan, PlanProduct, Product


class PlanProductInline(admin.TabularInline):
    model = PlanProduct
    extra = 0
    autocomplete_fields = ('product',)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'plan_type', 'archived', 'date')
    list_filter = ('plan_type', 'archived')
    search_fields = ('title', 'client__user__first_name', 'client__user__last_name')
    inlines = [PlanProductInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'url', 'active')
    list_filter = ('active',)
    list_editable = ('active',)
    search_fields = ('name', 'brand', 'description')

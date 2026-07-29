from django.contrib import admin

from .models import BodyMeasurement, Exercise, StrengthPR, EnduranceTestType, EnduranceTest


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)


@admin.register(EnduranceTestType)
class EnduranceTestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'lower_is_better', 'order')
    list_editable = ('order',)


@admin.register(BodyMeasurement)
class BodyMeasurementAdmin(admin.ModelAdmin):
    list_display = ('client', 'date', 'weight_kg', 'body_fat_pct')
    search_fields = ('client__user__first_name', 'client__user__last_name')


@admin.register(StrengthPR)
class StrengthPRAdmin(admin.ModelAdmin):
    list_display = ('client', 'exercise', 'weight_kg', 'reps', 'date')


@admin.register(EnduranceTest)
class EnduranceTestAdmin(admin.ModelAdmin):
    list_display = ('client', 'test_type', 'value', 'date')

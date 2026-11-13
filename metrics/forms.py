from django import forms

from .body_map import POINTS
from .models import BodyMeasurement, StrengthPR, EnduranceTest, CircumferenceMeasurement

INPUT = (
    'block w-full rounded-xl border-gray-300 bg-white px-3 py-2.5 '
    'text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-brand-500 '
    'focus:ring-brand-500 sm:text-sm'
)


def _style(fields):
    for field in fields.values():
        css = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = (css + ' ' + INPUT).strip()


class BodyMeasurementForm(forms.ModelForm):
    class Meta:
        model = BodyMeasurement
        fields = ['date', 'weight_kg', 'body_fat_pct', 'muscle_mass_pct', 'water_pct',
                  'visceral_fat', 'basal_metabolism', 'notes']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class StrengthPRForm(forms.ModelForm):
    class Meta:
        model = StrengthPR
        fields = ['exercise', 'date', 'weight_kg', 'reps']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class EnduranceTestForm(forms.ModelForm):
    class Meta:
        model = EnduranceTest
        fields = ['test_type', 'date', 'value']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class CircumferenceMeasurementForm(forms.ModelForm):
    class Meta:
        model = CircumferenceMeasurement
        fields = ['date'] + [p['field'] for p in POINTS] + ['notes']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)
        for p in POINTS:
            self.fields[p['field']].widget.attrs.update({
                'x-model.number': f"values.{p['field']}",
                'inputmode': 'decimal',
                'placeholder': '—',
                'step': '0.5',
                'class': ('w-12 rounded-full border-0 bg-transparent px-1 py-1.5 text-center '
                           'text-xs font-bold text-gray-900 placeholder:text-gray-400 '
                           'focus:ring-0 focus:outline-none'),
            })

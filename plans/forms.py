from django import forms

from .models import Plan

INPUT = (
    'block w-full rounded-xl border-surface-border bg-surface-secondary px-3 py-2.5 '
    'text-gray-100 placeholder:text-gray-500 shadow-sm focus:border-brand-500 '
    'focus:ring-brand-500 sm:text-sm'
)


class PlanForm(forms.ModelForm):
    archive_previous = forms.BooleanField(
        label='Archivar el plan anterior de este tipo', required=False, initial=True)

    class Meta:
        model = Plan
        fields = ['plan_type', 'title', 'content', 'pdf', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = (
                    'h-5 w-5 rounded border-surface-border bg-surface-secondary '
                    'text-brand-500 focus:ring-brand-500')
            else:
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (css + ' ' + INPUT).strip()

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('content') and not cleaned.get('pdf'):
            raise forms.ValidationError('Añade contenido de texto o un PDF (al menos uno).')
        return cleaned

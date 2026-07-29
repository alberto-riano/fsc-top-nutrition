from django import forms

from .models import Bono, Session

INPUT = (
    'block w-full rounded-xl border-surface-border bg-surface-secondary px-3 py-2.5 '
    'text-gray-100 placeholder:text-gray-500 shadow-sm focus:border-brand-500 '
    'focus:ring-brand-500 sm:text-sm'
)


def _style(fields):
    for field in fields.values():
        css = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = (css + ' ' + INPUT).strip()


class BonoForm(forms.ModelForm):
    class Meta:
        model = Bono
        fields = ['bono_type', 'sessions_total', 'price', 'purchase_date', 'expiry_date', 'notes']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['bono', 'date', 'session_type', 'notes']
        widgets = {
            'date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].input_formats = ['%Y-%m-%dT%H:%M']
        if client is not None:
            # Solo bonos no archivados del cliente.
            self.fields['bono'].queryset = client.bonos.filter(archived=False)
            self.fields['bono'].label_from_instance = (
                lambda b: f'{b.get_bono_type_display()} · quedan {b.sessions_left}')
        _style(self.fields)

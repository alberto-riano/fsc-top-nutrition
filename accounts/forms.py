from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, PasswordChangeForm

INPUT_CLASS = (
    'block w-full rounded-xl border-surface-border bg-surface-secondary px-3 py-2.5 '
    'text-gray-100 placeholder:text-gray-500 shadow-sm focus:border-brand-500 '
    'focus:ring-brand-500 sm:text-sm'
)


def _style(fields):
    for field in fields.values():
        if isinstance(field.widget, forms.CheckboxInput):
            continue
        css = field.widget.attrs.get('class', '')
        field.widget.attrs['class'] = (css + ' ' + INPUT_CLASS).strip()


class ProfileForm(forms.ModelForm):
    """Datos que el propio usuario (entrenador o cliente) puede editar."""

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'phone', 'avatar']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'phone': 'Teléfono',
            'avatar': 'Foto',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class StyledSetPasswordForm(SetPasswordForm):
    """SetPasswordForm con estilos de la app (usado en el alta por invitación)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)

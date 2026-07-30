from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import ClientProfile

User = get_user_model()

INPUT = (
    'block w-full rounded-xl border-gray-300 bg-white px-3 py-2.5 '
    'text-gray-900 placeholder:text-gray-400 shadow-sm focus:border-brand-500 '
    'focus:ring-brand-500 sm:text-sm'
)
CHECKBOX = 'h-5 w-5 rounded border-gray-300 bg-white text-brand-500 focus:ring-brand-500'


class ClientForm(forms.ModelForm):
    """
    Alta y edición de un cliente. Incluye los datos de identidad del usuario
    (nombre, email, teléfono) además del perfil. La contraseña inicial es
    opcional: si se deja vacía en el alta, se genera un enlace de invitación.
    """

    first_name = forms.CharField(label='Nombre', max_length=150)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=False)
    email = forms.EmailField(label='Email (acceso)')
    phone = forms.CharField(label='Teléfono', max_length=20, required=False)
    initial_password = forms.CharField(
        label='Contraseña inicial', required=False, widget=forms.PasswordInput,
        help_text='Opcional. Si la dejas vacía podrás generar un enlace de invitación.')

    class Meta:
        model = ClientProfile
        fields = [
            'profile_type', 'start_date', 'goal', 'active',
            'birth_date', 'position', 'guardian_name', 'guardian_phone',
            'internal_notes',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'goal': forms.Textarea(attrs={'rows': 2}),
            'internal_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prefill de los datos del usuario en edición. Ojo: el pk (UUID) se genera
        # con default, así que un objeto sin guardar ya tiene pk; el criterio de
        # "estamos editando" es que la instancia no esté en estado de alta.
        self._editing = not self.instance._state.adding
        if self._editing:
            u = self.instance.user
            self.fields['first_name'].initial = u.first_name
            self.fields['last_name'].initial = u.last_name
            self.fields['email'].initial = u.email
            self.fields['phone'].initial = u.phone
            # En edición no forzamos cambiar la contraseña.
            self.fields['initial_password'].label = 'Restablecer contraseña'
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = CHECKBOX
            else:
                css = field.widget.attrs.get('class', '')
                field.widget.attrs['class'] = (css + ' ' + INPUT).strip()

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if getattr(self, '_editing', False):
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email

    def clean_initial_password(self):
        pwd = self.cleaned_data.get('initial_password', '')
        if pwd:
            validate_password(pwd)
        return pwd

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('profile_type') == ClientProfile.PROFILE_FUTBOLISTA:
            if not cleaned.get('birth_date'):
                self.add_error('birth_date', 'Obligatoria para un perfil de futbolista.')
            if not cleaned.get('guardian_name'):
                self.add_error('guardian_name', 'Indica el nombre del tutor (es menor).')
        return cleaned

from django.contrib import messages
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.utils.http import urlsafe_base64_decode

from .forms import ProfileForm, StyledPasswordChangeForm, StyledSetPasswordForm


@login_required
def profile(request):
    """El usuario edita sus propios datos (nombre, teléfono, foto)."""
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def password_change(request):
    """Cambio de contraseña del propio usuario."""
    if request.method == 'POST':
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('accounts:profile')
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, 'accounts/password_change.html', {'form': form})


def accept_invite(request, uidb64, token):
    """
    El cliente establece su contraseña desde el enlace de invitación que le
    genera el entrenador. Valida el token (mismo generador que el reset de
    contraseña), activa la cuenta y deja la sesión iniciada.
    """
    try:
        user_id = urlsafe_base64_decode(uidb64).decode()
        user = get_user_model().objects.get(pk=user_id)
    except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return render(request, 'accounts/invite_invalid.html', status=400)

    if request.method == 'POST':
        form = StyledSetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])
            login(request, user, backend='accounts.backends.EmailBackend')
            messages.success(request, '¡Bienvenido/a! Tu cuenta ya está activa.')
            return redirect('dashboard:home')
    else:
        form = StyledSetPasswordForm(user)
    return render(request, 'accounts/invite_set_password.html', {'form': form, 'invited_user': user})

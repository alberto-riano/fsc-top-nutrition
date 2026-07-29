from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import trainer_required
from clients.models import ClientProfile
from .forms import BonoForm, SessionForm
from .models import Bono, Session


def _detail(client_pk, tab='bonos'):
    return redirect(f"{_detail_url(client_pk)}?tab={tab}")


def _detail_url(client_pk):
    from django.urls import reverse
    return reverse('clients:detail', kwargs={'pk': client_pk})


@trainer_required
def bono_create(request, client_pk):
    client = get_object_or_404(ClientProfile, pk=client_pk)
    if request.method == 'POST':
        form = BonoForm(request.POST)
        if form.is_valid():
            bono = form.save(commit=False)
            bono.client = client
            bono.save()
            messages.success(request, 'Bono creado.')
            return _detail(client_pk)
    else:
        form = BonoForm()
    return render(request, 'bonos/form.html', {'form': form, 'client': client, 'is_create': True})


@trainer_required
def bono_edit(request, pk):
    bono = get_object_or_404(Bono.objects.select_related('client'), pk=pk)
    if request.method == 'POST':
        form = BonoForm(request.POST, instance=bono)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bono actualizado.')
            return _detail(bono.client_id)
    else:
        form = BonoForm(instance=bono)
    return render(request, 'bonos/form.html', {'form': form, 'client': bono.client, 'is_create': False})


@trainer_required
@require_POST
def bono_archive(request, pk):
    bono = get_object_or_404(Bono, pk=pk)
    bono.archived = not bono.archived
    bono.save(update_fields=['archived'])
    messages.success(request, 'Bono archivado.' if bono.archived else 'Bono reactivado.')
    return _detail(bono.client_id)


@trainer_required
@require_POST
def bono_delete(request, pk):
    bono = get_object_or_404(Bono, pk=pk)
    client_id = bono.client_id
    bono.delete()
    messages.success(request, 'Bono eliminado.')
    return _detail(client_id)


@trainer_required
@require_POST
def mark_session_today(request, client_pk):
    """Registra una sesión de hoy en el bono activo (2 clics desde la ficha)."""
    client = get_object_or_404(ClientProfile, pk=client_pk)
    bono = client.active_bono
    if bono is None:
        messages.error(request, 'No hay ningún bono activo con sesiones disponibles.')
        return _detail(client_pk)
    Session.objects.create(
        bono=bono,
        date=timezone.now(),
        session_type=bono.bono_type,
        notes=request.POST.get('notes', ''),
    )
    left = bono.sessions_left
    if left == 0:
        messages.warning(request, 'Sesión registrada. El bono queda agotado.')
    else:
        messages.success(request, f'Sesión registrada. Quedan {left} sesiones.')
    return _detail(client_pk)


@trainer_required
def session_create(request, client_pk):
    client = get_object_or_404(ClientProfile, pk=client_pk)
    if request.method == 'POST':
        form = SessionForm(request.POST, client=client)
        if form.is_valid():
            session = form.save(commit=False)
            # Seguridad: el bono debe pertenecer a este cliente.
            if session.bono.client_id != client.pk:
                messages.error(request, 'Ese bono no pertenece a este cliente.')
                return _detail(client_pk)
            session.save()
            messages.success(request, 'Sesión registrada.')
            return _detail(client_pk)
    else:
        initial = {'date': timezone.localtime().strftime('%Y-%m-%dT%H:%M')}
        bono = client.active_bono
        if bono:
            initial['bono'] = bono.pk
            initial['session_type'] = bono.bono_type
        form = SessionForm(client=client, initial=initial)
    return render(request, 'bonos/session_form.html', {'form': form, 'client': client})


@trainer_required
@require_POST
def session_delete(request, pk):
    """Borra una sesión mal apuntada; el contador del bono se restaura solo."""
    session = get_object_or_404(Session.objects.select_related('bono'), pk=pk)
    client_id = session.bono.client_id
    session.delete()
    messages.success(request, 'Sesión eliminada. El contador del bono se ha restaurado.')
    return _detail(client_id, tab='bonos')

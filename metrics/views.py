from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import trainer_required
from clients.models import ClientProfile
from .forms import BodyMeasurementForm, StrengthPRForm, EnduranceTestForm
from .models import BodyMeasurement, StrengthPR, EnduranceTest


def _detail(client_pk, tab='metricas'):
    return redirect(f"{reverse('clients:detail', kwargs={'pk': client_pk})}?tab={tab}")


def _quick_add(request, client_pk, form_class, template, title):
    client = get_object_or_404(ClientProfile, pk=client_pk)
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.client = client
            obj.save()
            messages.success(request, f'{title} registrado.')
            return _detail(client_pk)
    else:
        form = form_class()
    return render(request, template, {'form': form, 'client': client, 'title': title})


@trainer_required
def body_create(request, client_pk):
    return _quick_add(request, client_pk, BodyMeasurementForm,
                      'metrics/body_form.html', 'Medición corporal')


@trainer_required
def pr_create(request, client_pk):
    return _quick_add(request, client_pk, StrengthPRForm,
                      'metrics/pr_form.html', 'Récord de fuerza')


@trainer_required
def test_create(request, client_pk):
    return _quick_add(request, client_pk, EnduranceTestForm,
                      'metrics/test_form.html', 'Test de resistencia')


@trainer_required
@require_POST
def body_delete(request, pk):
    obj = get_object_or_404(BodyMeasurement, pk=pk)
    client_id = obj.client_id
    obj.delete()
    messages.success(request, 'Medición eliminada.')
    return _detail(client_id)


@trainer_required
@require_POST
def pr_delete(request, pk):
    obj = get_object_or_404(StrengthPR, pk=pk)
    client_id = obj.client_id
    obj.delete()
    messages.success(request, 'Récord eliminado.')
    return _detail(client_id)


@trainer_required
@require_POST
def test_delete(request, pk):
    obj = get_object_or_404(EnduranceTest, pk=pk)
    client_id = obj.client_id
    obj.delete()
    messages.success(request, 'Test eliminado.')
    return _detail(client_id)

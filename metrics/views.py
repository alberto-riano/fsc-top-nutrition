from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import trainer_required
from clients.models import ClientProfile
from .body_map import POINTS, FIELD_NAMES
from .forms import BodyMeasurementForm, StrengthPRForm, EnduranceTestForm, CircumferenceMeasurementForm
from .models import BodyMeasurement, StrengthPR, EnduranceTest, CircumferenceMeasurement


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
def circumference_create(request, client_pk):
    client = get_object_or_404(ClientProfile, pk=client_pk)
    last = client.circumference_measurements.first()
    if request.method == 'POST':
        form = CircumferenceMeasurementForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.client = client
            obj.save()
            messages.success(request, 'Medidas corporales registradas.')
            return _detail(client_pk)
    else:
        form = CircumferenceMeasurementForm()

    field_points = []
    for p in POINTS:
        fp = dict(p)
        fp['bound_field'] = form[p['field']]
        field_points.append(fp)

    last_values = None
    if last:
        last_values = {f: (float(v) if (v := getattr(last, f)) is not None else None) for f in FIELD_NAMES}

    return render(request, 'metrics/circumference_form.html', {
        'form': form, 'client': client, 'title': 'Medidas corporales',
        'field_points': field_points, 'last': last, 'last_values': last_values,
    })


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


@trainer_required
@require_POST
def circumference_delete(request, pk):
    obj = get_object_or_404(CircumferenceMeasurement, pk=pk)
    client_id = obj.client_id
    obj.delete()
    messages.success(request, 'Medidas eliminadas.')
    return _detail(client_id)

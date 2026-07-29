from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from accounts.decorators import trainer_required
from clients.models import ClientProfile
from .forms import PlanForm
from .models import Plan


def _detail(client_pk, tab='planes'):
    return redirect(f"{reverse('clients:detail', kwargs={'pk': client_pk})}?tab={tab}")


@trainer_required
def plan_create(request, client_pk):
    client = get_object_or_404(ClientProfile, pk=client_pk)
    if request.method == 'POST':
        form = PlanForm(request.POST, request.FILES)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.client = client
            if form.cleaned_data.get('archive_previous'):
                client.plans.filter(plan_type=plan.plan_type, archived=False).update(archived=True)
            plan.save()
            messages.success(request, 'Plan guardado.')
            return _detail(client_pk)
    else:
        form = PlanForm()
    return render(request, 'plans/form.html', {'form': form, 'client': client, 'is_create': True})


@trainer_required
def plan_edit(request, pk):
    plan = get_object_or_404(Plan.objects.select_related('client'), pk=pk)
    if request.method == 'POST':
        form = PlanForm(request.POST, request.FILES, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plan actualizado.')
            return _detail(plan.client_id)
    else:
        form = PlanForm(instance=plan)
    return render(request, 'plans/form.html', {'form': form, 'client': plan.client, 'is_create': False})


@trainer_required
@require_POST
def plan_archive(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    plan.archived = not plan.archived
    plan.save(update_fields=['archived'])
    messages.success(request, 'Plan archivado.' if plan.archived else 'Plan reactivado.')
    return _detail(plan.client_id)


@trainer_required
@require_POST
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    client_id = plan.client_id
    plan.delete()
    messages.success(request, 'Plan eliminado.')
    return _detail(client_id)


@login_required
def plan_download(request, pk):
    """Descarga del PDF. Solo el entrenador o el propio cliente dueño del plan."""
    plan = get_object_or_404(Plan.objects.select_related('client__user'), pk=pk)
    user = request.user
    is_owner = plan.client.user_id == user.pk
    if not (user.is_trainer or is_owner):
        raise PermissionDenied
    if not plan.pdf:
        raise PermissionDenied
    return FileResponse(plan.pdf.open('rb'), as_attachment=True, filename=plan.pdf.name.split('/')[-1])

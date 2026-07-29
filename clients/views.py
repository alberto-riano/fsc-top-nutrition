from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import trainer_required
from metrics import charts
from metrics.models import Exercise, EnduranceTestType
from .forms import ClientForm
from .models import ClientProfile
from .services import create_client_user, invitation_url


@trainer_required
def client_list(request):
    q = (request.GET.get('q') or '').strip()
    profile_type = request.GET.get('tipo') or ''
    show = request.GET.get('estado') or 'activos'

    clients = ClientProfile.objects.select_related('user').prefetch_related('bonos__sessions')
    if q:
        clients = clients.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__phone__icontains=q)
        )
    if profile_type:
        clients = clients.filter(profile_type=profile_type)
    if show == 'activos':
        clients = clients.filter(active=True)
    elif show == 'inactivos':
        clients = clients.filter(active=False)

    clients = list(clients)
    low_alerts = [c for c in clients if c.active and c.low_sessions_alert]

    context = {
        'clients': clients,
        'q': q,
        'profile_type': profile_type,
        'show': show,
        'profile_choices': ClientProfile.PROFILE_CHOICES,
        'low_alerts': low_alerts,
        'total': len(clients),
    }
    return render(request, 'clients/list.html', context)


@trainer_required
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = create_client_user(
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    phone=form.cleaned_data['phone'],
                    password=form.cleaned_data.get('initial_password') or None,
                )
                profile = form.save(commit=False)
                profile.user = user
                profile.save()
            messages.success(request, f'Cliente «{profile.full_name}» creado.')
            if not form.cleaned_data.get('initial_password'):
                messages.info(
                    request,
                    'No definiste contraseña: genera el enlace de invitación desde la ficha.')
            return redirect('clients:detail', pk=profile.pk)
    else:
        form = ClientForm()
    return render(request, 'clients/form.html', {'form': form, 'is_create': True})


@trainer_required
def client_edit(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=profile)
        if form.is_valid():
            with transaction.atomic():
                user = profile.user
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.phone = form.cleaned_data['phone']
                new_password = form.cleaned_data.get('initial_password')
                if new_password:
                    user.set_password(new_password)
                    user.is_active = True
                user.save()
                form.save()
            messages.success(request, 'Ficha actualizada.')
            return redirect('clients:detail', pk=profile.pk)
    else:
        form = ClientForm(instance=profile)
    return render(request, 'clients/form.html', {'form': form, 'is_create': False, 'client': profile})


@trainer_required
def client_invite_link(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    url = invitation_url(request, profile.user)
    return render(request, 'clients/invite_link.html', {'client': profile, 'invite_url': url})


@trainer_required
def client_detail(request, pk):
    profile = get_object_or_404(ClientProfile.objects.select_related('user'), pk=pk)
    tab = request.GET.get('tab') or 'resumen'

    bonos = list(profile.bonos.prefetch_related('sessions').all())
    active_bono = profile.active_bono
    recent_sessions = []
    for b in bonos:
        for s in b.sessions.all():
            recent_sessions.append(s)
    recent_sessions.sort(key=lambda s: s.date, reverse=True)

    context = {
        'client': profile,
        'tab': tab,
        'bonos': bonos,
        'active_bono': active_bono,
        'sessions': recent_sessions[:30],
        'session_count': len(recent_sessions),
        # Métricas
        'body_measurements': list(profile.body_measurements.all()[:20]),
        'strength_prs': list(profile.strength_prs.select_related('exercise').all()[:30]),
        'endurance_tests': list(profile.endurance_tests.select_related('test_type').all()[:30]),
        'plans': list(profile.plans.all()),
        # Catálogos para los formularios rápidos
        'exercises': list(Exercise.objects.all()),
        'test_types': list(EnduranceTestType.objects.all()),
        # Gráficas (dicts; la plantilla las incrusta con json_script)
        'body_chart': charts.body_series(profile),
        'strength_chart': charts.strength_series(profile),
        'endurance_chart': charts.endurance_series(profile),
    }
    return render(request, 'clients/detail.html', context)

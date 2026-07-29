from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.decorators import client_required
from clients.models import ClientProfile
from metrics import charts


@login_required
def home(request):
    """Reparte según el rol: panel del entrenador o panel del cliente."""
    if request.user.is_trainer:
        return _trainer_home(request)
    return _client_home(request)


def _trainer_home(request):
    clients = list(
        ClientProfile.objects.select_related('user')
        .prefetch_related('bonos__sessions')
        .filter(active=True)
    )
    low_alerts = [c for c in clients if c.low_sessions_alert]
    # Bonos por caducar (con fecha de caducidad en los próximos 30 días).
    from datetime import date, timedelta
    soon = date.today() + timedelta(days=30)
    expiring = []
    for c in clients:
        b = c.active_bono
        if b and b.expiry_date and date.today() <= b.expiry_date <= soon:
            expiring.append((c, b))

    by_type = {}
    for c in clients:
        by_type[c.profile_type] = by_type.get(c.profile_type, 0) + 1

    context = {
        'clients': clients[:8],
        'total_clients': len(clients),
        'low_alerts': low_alerts,
        'expiring': expiring,
        'count_completo': by_type.get('completo', 0),
        'count_basico': by_type.get('basico', 0),
        'count_futbolista': by_type.get('futbolista', 0),
    }
    return render(request, 'dashboard/trainer_home.html', context)


def _client_home(request):
    if not hasattr(request.user, 'client_profile'):
        # Usuario sin perfil (p. ej. staff sin ficha): a su perfil de cuenta.
        return redirect('accounts:profile')
    profile = request.user.client_profile
    context = {
        'client': profile,
        'active_bono': profile.active_bono,
        'latest_body': profile.body_measurements.first(),
        'body_chart': charts.body_series(profile),
        'active_routine': profile.plans.filter(plan_type='rutina', archived=False).first(),
        'active_nutrition': profile.plans.filter(plan_type='alimentacion', archived=False).first(),
    }
    return render(request, 'dashboard/client_home.html', context)


@client_required
def my_progress(request):
    profile = request.user.client_profile
    context = {
        'client': profile,
        'body_measurements': list(profile.body_measurements.all()[:20]),
        'strength_prs': list(profile.strength_prs.select_related('exercise').all()[:30]),
        'endurance_tests': list(profile.endurance_tests.select_related('test_type').all()[:30]),
        'body_chart': charts.body_series(profile),
        'strength_chart': charts.strength_series(profile),
        'endurance_chart': charts.endurance_series(profile),
    }
    return render(request, 'dashboard/my_progress.html', context)


@client_required
def my_bonos(request):
    profile = request.user.client_profile
    bonos = list(profile.bonos.prefetch_related('sessions').all())
    sessions = []
    for b in bonos:
        for s in b.sessions.all():
            sessions.append(s)
    sessions.sort(key=lambda s: s.date, reverse=True)
    context = {
        'client': profile,
        'active_bono': profile.active_bono,
        'bonos': bonos,
        'sessions': sessions,
    }
    return render(request, 'dashboard/my_bonos.html', context)


@client_required
def my_plans(request):
    profile = request.user.client_profile
    context = {
        'client': profile,
        'routines': list(profile.plans.filter(plan_type='rutina')),
        'nutrition': list(profile.plans.filter(plan_type='alimentacion')),
    }
    return render(request, 'dashboard/my_plans.html', context)

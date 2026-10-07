"""
Datos de demostración para enseñar TopTrack recién desplegado.

Crea (idempotente por email):
  · el entrenador/admin,
  · 3 clientes (uno de cada perfil) con bonos, sesiones, métricas de varios
    meses y planes de ejemplo.

Uso:  python manage.py seed_demo
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from bonos.models import Bono, Session
from clients.models import ClientProfile
from metrics.models import (BodyMeasurement, Exercise, StrengthPR,
                            EnduranceTestType, EnduranceTest)
from plans.models import Plan

User = get_user_model()


def _sample_pdf_bytes(title, lines):
    """PDF de una página con Pillow (sin dependencias extra tipo reportlab)."""
    width, height = 1000, 1400
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.load_default(size=40)
        font_body = ImageFont.load_default(size=26)
    except TypeError:
        # Pillow < 9.2 no soporta el argumento size.
        font_title = font_body = ImageFont.load_default()

    draw.text((60, 60), title, fill='black', font=font_title)
    y = 140
    for line in lines:
        draw.text((60, y), line, fill='black', font=font_body)
        y += 40

    buffer = BytesIO()
    img.save(buffer, format='PDF')
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Crea datos de demostración (admin + 3 clientes con historial)."

    def handle(self, *args, **opts):
        random.seed(42)
        admin = self._trainer()
        self._quick_login_trainer()
        self._ensure_catalog()

        self._completo()
        self._basico()
        self._futbolista()
        self._alberto_azul()

        self.stdout.write(self.style.SUCCESS(
            'Demo creada. Entrena con: admin@toptrack.local / admin (o el que definiste), '
            'o con admin / admin para pruebas rápidas. '
            'Clientes de ejemplo: ana@demo.com, luis@demo.com, marco@demo.com, '
            'alberto@demo.com (contraseña: demo1234).'))

    # ------------------------------------------------------------------ utils
    def _trainer(self):
        admin, created = User.objects.get_or_create(
            email='admin@toptrack.local',
            defaults={'username': 'admin@toptrack.local', 'role': 'admin',
                      'first_name': 'Entrenador', 'is_staff': True, 'is_superuser': True})
        if created:
            admin.set_password('admin')
            admin.save()
        return admin

    def _quick_login_trainer(self):
        """Cuenta de entrenador con credenciales cortas (solo para pruebas)."""
        admin, created = User.objects.get_or_create(
            email='admin',
            defaults={'username': 'admin-quick', 'role': 'admin',
                      'first_name': 'Admin', 'is_staff': True, 'is_superuser': True})
        if created:
            admin.set_password('admin')
            admin.save()
        return admin

    def _ensure_catalog(self):
        if not Exercise.objects.exists():
            for i, n in enumerate(['Peso muerto', 'Sentadilla', 'Press banca', 'Press hombro', 'Remo']):
                Exercise.objects.get_or_create(name=n, defaults={'order': i})
        if not EnduranceTestType.objects.exists():
            EnduranceTestType.objects.get_or_create(name='Plancha', defaults={'unit': 'segundos'})

    def _client(self, email, first, last, phone, profile_type, **profile_kwargs):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'username': f'demo-{email.split("@")[0]}', 'role': 'cliente',
                      'first_name': first, 'last_name': last, 'phone': phone, 'is_active': True})
        if created:
            user.set_password('demo1234')
            user.save()
        profile, _ = ClientProfile.objects.get_or_create(
            user=user,
            defaults={'profile_type': profile_type,
                      'start_date': date.today() - timedelta(days=180), **profile_kwargs})
        return profile

    def _bono_with_sessions(self, client, bono_type, total, used, days_ago=120):
        bono, created = Bono.objects.get_or_create(
            client=client, bono_type=bono_type, sessions_total=total,
            defaults={'price': Decimal('300.00'),
                      'purchase_date': date.today() - timedelta(days=days_ago)})
        if created:
            for i in range(used):
                d = timezone.now() - timedelta(days=(used - i) * 5, hours=random.randint(0, 6))
                Session.objects.create(bono=bono, date=d, session_type=bono_type,
                                       notes=random.choice(['', 'Buena sesión', 'Trabajo de core', '']))
        return bono

    # --------------------------------------------------------------- clientes
    def _completo(self):
        c = self._client('ana@demo.com', 'Ana', 'García', '600111222', 'completo',
                         goal='Perder grasa y ganar fuerza en tren inferior.')
        self._bono_with_sessions(c, 'individual', 10, 8)
        # 6 meses de composición corporal
        if not c.body_measurements.exists():
            w = 72.0; fat = 30.0; mus = 34.0
            for k in range(6):
                d = date.today() - timedelta(days=(6 - k) * 30)
                BodyMeasurement.objects.create(
                    client=c, date=d,
                    weight_kg=Decimal(str(round(w, 1))),
                    body_fat_pct=Decimal(str(round(fat, 1))),
                    muscle_mass_pct=Decimal(str(round(mus, 1))),
                    water_pct=Decimal('50.0'),
                    visceral_fat=Decimal('8.0'),
                    basal_metabolism=1450)
                w -= random.uniform(0.5, 1.2); fat -= random.uniform(0.4, 1.0); mus += random.uniform(0.2, 0.6)
        # PRs
        if not c.strength_prs.exists():
            for name, base in [('Sentadilla', 40), ('Peso muerto', 55), ('Press banca', 25)]:
                ex = Exercise.objects.filter(name=name).first()
                if not ex:
                    continue
                val = base
                for k in range(5):
                    StrengthPR.objects.create(
                        client=c, exercise=ex, date=date.today() - timedelta(days=(5 - k) * 25),
                        weight_kg=Decimal(str(val)), reps=1)
                    val += random.randint(2, 6)
        # Tests
        if not c.endurance_tests.exists():
            tt = EnduranceTestType.objects.filter(name='Plancha').first()
            if tt:
                v = 45
                for k in range(5):
                    EnduranceTest.objects.create(
                        client=c, test_type=tt, date=date.today() - timedelta(days=(5 - k) * 25),
                        value=Decimal(str(v)))
                    v += random.randint(5, 15)
        # Planes
        if not c.plans.exists():
            routine = Plan.objects.create(
                client=c, plan_type='rutina', title='Rutina full-body 3 días',
                content='Día A: sentadilla, press banca, remo.\nDía B: peso muerto, press hombro, dominadas.\nDía C: circuito metabólico.',
                date=date.today() - timedelta(days=20))
            routine_pdf = _sample_pdf_bytes('Rutina full-body · Ana García', [
                'Frecuencia: 3 días/semana, no consecutivos',
                '',
                'DÍA A',
                '  Sentadilla          4x10',
                '  Press banca         4x10',
                '  Remo con barra      4x10',
                '  Plancha             3x40s',
                '',
                'DÍA B',
                '  Peso muerto         4x8',
                '  Press hombro        4x10',
                '  Dominadas asistidas 4x8',
                '  Rueda abdominal     3x10',
                '',
                'DÍA C (circuito metabólico x4 vueltas)',
                '  Burpees             12',
                '  Zancadas            16',
                '  Remo mancuerna      12 c/lado',
                '  Mountain climbers   30s',
                '',
                'Descanso entre series: 60-90s. Calentamiento 5-10 min antes de cada día.',
            ])
            routine.pdf.save('rutina-fullbody-ana.pdf', ContentFile(routine_pdf), save=True)

            nutrition = Plan.objects.create(
                client=c, plan_type='alimentacion', title='Plan hipocalórico 1600 kcal',
                content='Desayuno: avena + fruta.\nComida: proteína + verdura + arroz.\nCena: pescado + ensalada.',
                date=date.today() - timedelta(days=20))
            pdf_bytes = _sample_pdf_bytes('Plan de alimentación · Ana García', [
                'Objetivo: 1600 kcal/día · déficit moderado',
                '',
                'Desayuno (350 kcal)',
                '  Avena con leche + fruta + puñado de frutos secos',
                '',
                'Media mañana (150 kcal)',
                '  Yogur natural + fruta',
                '',
                'Comida (500 kcal)',
                '  Pechuga de pollo o pescado + verdura + arroz/patata',
                '',
                'Merienda (150 kcal)',
                '  Tostada integral + aguacate',
                '',
                'Cena (450 kcal)',
                '  Pescado o huevo + ensalada variada',
                '',
                'Hidratación: 2 L de agua al día.',
                'Suplementación: no necesaria salvo indicación del entrenador.',
            ])
            nutrition.pdf.save('plan-alimentacion-ana.pdf', ContentFile(pdf_bytes), save=True)

    def _basico(self):
        c = self._client('luis@demo.com', 'Luis', 'Martín', '600333444', 'basico',
                         goal='Mantenerse activo y controlar el peso.')
        self._bono_with_sessions(c, 'grupo', 20, 19)  # queda 1 -> aviso
        if not c.body_measurements.exists():
            w = 85.0; fat = 24.0
            for k in range(5):
                BodyMeasurement.objects.create(
                    client=c, date=date.today() - timedelta(days=(5 - k) * 30),
                    weight_kg=Decimal(str(round(w, 1))),
                    body_fat_pct=Decimal(str(round(fat, 1))),
                    muscle_mass_pct=Decimal('38.0'))
                w -= random.uniform(0.3, 0.8); fat -= random.uniform(0.2, 0.6)

    def _futbolista(self):
        c = self._client('marco@demo.com', 'Marco', 'Ruiz', '600555666', 'futbolista',
                         goal='Mejorar velocidad y potencia de salto.',
                         birth_date=date.today() - timedelta(days=365 * 13),
                         position='Centrocampista',
                         guardian_name='Elena Ruiz', guardian_phone='600777888')
        self._bono_with_sessions(c, 'futbol', 12, 5)
        if not c.endurance_tests.exists():
            sprint = EnduranceTestType.objects.get_or_create(
                name='Sprint 30m', defaults={'unit': 'segundos', 'lower_is_better': True})[0]
            salto = EnduranceTestType.objects.get_or_create(
                name='Salto vertical', defaults={'unit': 'metros'})[0]
            sv = 5.2
            for k in range(5):
                EnduranceTest.objects.create(client=c, test_type=sprint,
                                             date=date.today() - timedelta(days=(5 - k) * 25),
                                             value=Decimal(str(round(sv, 1))))
                sv -= random.uniform(0.05, 0.15)
            jv = 0.35
            for k in range(5):
                EnduranceTest.objects.create(client=c, test_type=salto,
                                             date=date.today() - timedelta(days=(5 - k) * 25),
                                             value=Decimal(str(round(jv, 2))))
                jv += random.uniform(0.01, 0.04)

    def _alberto_azul(self):
        c = self._client('alberto@demo.com', 'Alberto', 'Azul', '600123123', 'completo',
                         goal='Ganar masa muscular y fuerza en press banca.')
        self._bono_with_sessions(c, 'individual', 15, 6)
        if not c.body_measurements.exists():
            w = 78.0; fat = 20.0; mus = 40.0
            for k in range(6):
                BodyMeasurement.objects.create(
                    client=c, date=date.today() - timedelta(days=(6 - k) * 30),
                    weight_kg=Decimal(str(round(w, 1))),
                    body_fat_pct=Decimal(str(round(fat, 1))),
                    muscle_mass_pct=Decimal(str(round(mus, 1))),
                    water_pct=Decimal('55.0'), basal_metabolism=1780)
                w += random.uniform(0.2, 0.6); fat -= random.uniform(0.2, 0.5); mus += random.uniform(0.3, 0.7)
        if not c.strength_prs.exists():
            for name, base in [('Press banca', 60), ('Peso muerto', 90), ('Sentadilla', 80)]:
                ex = Exercise.objects.filter(name=name).first()
                if not ex:
                    continue
                val = base
                for k in range(5):
                    StrengthPR.objects.create(
                        client=c, exercise=ex, date=date.today() - timedelta(days=(5 - k) * 25),
                        weight_kg=Decimal(str(val)), reps=1)
                    val += random.randint(3, 7)
        if not c.endurance_tests.exists():
            tt = EnduranceTestType.objects.filter(name='Dominadas máximas').first() \
                or EnduranceTestType.objects.filter(name='Plancha').first()
            if tt:
                v = 8
                for k in range(5):
                    EnduranceTest.objects.create(
                        client=c, test_type=tt, date=date.today() - timedelta(days=(5 - k) * 25),
                        value=Decimal(str(v)))
                    v += random.randint(1, 3)
        if not c.plans.exists():
            routine = Plan.objects.create(
                client=c, plan_type='rutina', title='Rutina de hipertrofia (push/pull/legs)',
                content='Push: press banca, press militar, fondos.\nPull: dominadas, remo, curl.\nLegs: sentadilla, peso muerto, zancadas.',
                date=date.today() - timedelta(days=10))
            routine_pdf = _sample_pdf_bytes('Rutina push/pull/legs · Alberto Azul', [
                'Frecuencia: 6 días/semana (PPL x2)',
                '',
                'PUSH (pecho/hombro/tríceps)',
                '  Press banca          4x8',
                '  Press militar         4x8',
                '  Elevaciones laterales 3x12',
                '  Fondos en paralelas   3x10',
                '',
                'PULL (espalda/bíceps)',
                '  Dominadas lastradas   4x6',
                '  Remo con barra        4x8',
                '  Curl de bíceps        3x12',
                '  Face pull             3x15',
                '',
                'LEGS (pierna completa)',
                '  Sentadilla            4x6',
                '  Peso muerto rumano    4x8',
                '  Zancadas con peso     3x12 c/pierna',
                '  Gemelo en máquina     4x15',
                '',
                'Descanso: 90-120s en básicos, 60s en accesorios.',
            ])
            routine.pdf.save('rutina-ppl-alberto.pdf', ContentFile(routine_pdf), save=True)

            Plan.objects.create(client=c, plan_type='alimentacion', title='Plan de volumen 2600 kcal',
                                content='Superávit calórico moderado.\n2 g proteína/kg.\n5 comidas al día.',
                                date=date.today() - timedelta(days=10))

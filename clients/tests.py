from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bonos.models import Bono
from metrics.models import BodyMeasurement
from plans.models import Plan
from .models import ClientProfile

User = get_user_model()


def trainer():
    return User.objects.create_user(username='t@demo.com', email='t@demo.com', password='x', role='admin')


def client_profile(email='c@demo.com', profile_type='completo'):
    u = User.objects.create_user(username=email, email=email, password='x', role='cliente')
    return ClientProfile.objects.create(user=u, profile_type=profile_type)


class ProfileVisibilityTests(TestCase):
    def test_completo_shows_all(self):
        p = client_profile(profile_type='completo')
        self.assertTrue(p.shows_body_composition)
        self.assertTrue(p.shows_strength_prs)
        self.assertTrue(p.shows_endurance_tests)
        self.assertTrue(p.shows_plans)

    def test_basico_only_body(self):
        p = client_profile(profile_type='basico')
        self.assertTrue(p.shows_body_composition)
        self.assertFalse(p.shows_strength_prs)
        self.assertFalse(p.shows_endurance_tests)
        self.assertFalse(p.shows_plans)

    def test_futbolista_tests_no_prs(self):
        p = client_profile(profile_type='futbolista')
        self.assertFalse(p.shows_strength_prs)
        self.assertTrue(p.shows_endurance_tests)
        self.assertFalse(p.shows_body_composition)


class PermissionTests(TestCase):
    def setUp(self):
        self.trainer = trainer()
        self.p1 = client_profile('ana@demo.com')
        self.p2 = client_profile('bob@demo.com')

    def test_client_cannot_access_admin_views(self):
        self.client.force_login(self.p1.user)
        for name, args in [
            ('clients:list', []),
            ('clients:detail', [self.p2.pk]),
            ('clients:create', []),
            ('bonos:create', [self.p2.pk]),
            ('metrics:body_create', [self.p2.pk]),
        ]:
            resp = self.client.get(reverse(name, args=args))
            self.assertEqual(resp.status_code, 403, f'{name} debería ser 403 para un cliente')

    def test_client_cannot_download_other_clients_pdf(self):
        plan = Plan.objects.create(client=self.p2, plan_type='rutina', title='x', content='y')
        # Sin PDF real: la vista niega por permiso antes de servir archivo.
        self.client.force_login(self.p1.user)
        resp = self.client.get(reverse('plans:download', args=[plan.pk]))
        self.assertEqual(resp.status_code, 403)

    def test_trainer_can_access_client_detail(self):
        self.client.force_login(self.trainer)
        resp = self.client.get(reverse('clients:detail', args=[self.p1.pk]))
        self.assertEqual(resp.status_code, 200)


class ClientCreateTests(TestCase):
    def test_trainer_creates_client_with_password(self):
        self.client.force_login(trainer())
        resp = self.client.post(reverse('clients:create'), {
            'first_name': 'Nuevo', 'last_name': 'Cliente', 'email': 'nuevo@demo.com',
            'phone': '600000000', 'initial_password': 'segura1234',
            'profile_type': 'completo', 'start_date': '2026-01-01', 'active': 'on',
            'goal': '', 'internal_notes': '',
            'birth_date': '', 'position': '', 'guardian_name': '', 'guardian_phone': '',
        })
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(email='nuevo@demo.com')
        self.assertTrue(u.is_active)
        self.assertTrue(u.check_password('segura1234'))
        self.assertEqual(u.client_profile.profile_type, 'completo')

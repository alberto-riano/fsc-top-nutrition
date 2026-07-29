from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import ClientProfile
from .models import Bono, Session

User = get_user_model()


def make_client_profile(email='c@demo.com'):
    user = User.objects.create_user(username=email, email=email, password='x', role='cliente')
    return ClientProfile.objects.create(user=user, profile_type='completo')


class BonoStatusTests(TestCase):
    def setUp(self):
        self.client_profile = make_client_profile()

    def test_session_count_discounts_from_bono(self):
        bono = Bono.objects.create(client=self.client_profile, sessions_total=5)
        self.assertEqual(bono.sessions_left, 5)
        Session.objects.create(bono=bono, date=timezone.now())
        Session.objects.create(bono=bono, date=timezone.now())
        self.assertEqual(bono.sessions_used, 2)
        self.assertEqual(bono.sessions_left, 3)
        self.assertEqual(bono.status, 'activo')

    def test_bono_becomes_exhausted(self):
        bono = Bono.objects.create(client=self.client_profile, sessions_total=2)
        Session.objects.create(bono=bono, date=timezone.now())
        Session.objects.create(bono=bono, date=timezone.now())
        self.assertEqual(bono.sessions_left, 0)
        self.assertEqual(bono.status, 'agotado')

    def test_deleting_session_restores_counter(self):
        bono = Bono.objects.create(client=self.client_profile, sessions_total=3)
        s = Session.objects.create(bono=bono, date=timezone.now())
        self.assertEqual(bono.sessions_left, 2)
        s.delete()
        self.assertEqual(bono.sessions_left, 3)

    def test_bono_expired_status(self):
        bono = Bono.objects.create(
            client=self.client_profile, sessions_total=5,
            expiry_date=date.today() - timedelta(days=1))
        self.assertEqual(bono.status, 'caducado')

    def test_archived_status_and_active_bono_selection(self):
        active = Bono.objects.create(client=self.client_profile, sessions_total=5)
        archived = Bono.objects.create(client=self.client_profile, sessions_total=5, archived=True)
        self.assertEqual(archived.status, 'archivado')
        self.assertEqual(self.client_profile.active_bono, active)

    def test_low_sessions_alert(self):
        bono = Bono.objects.create(client=self.client_profile, sessions_total=3)
        Session.objects.create(bono=bono, date=timezone.now())
        self.assertTrue(self.client_profile.low_sessions_alert)  # quedan 2


class MarkSessionTodayViewTests(TestCase):
    def setUp(self):
        self.trainer = User.objects.create_user(
            username='t@demo.com', email='t@demo.com', password='x', role='admin')
        self.profile = make_client_profile('client2@demo.com')

    def test_mark_today_creates_session(self):
        bono = Bono.objects.create(client=self.profile, sessions_total=5)
        self.client.force_login(self.trainer)
        resp = self.client.post(reverse('bonos:mark_today', args=[self.profile.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(bono.sessions_used, 1)

    def test_mark_today_without_active_bono(self):
        self.client.force_login(self.trainer)
        resp = self.client.post(reverse('bonos:mark_today', args=[self.profile.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Session.objects.count(), 0)

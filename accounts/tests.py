from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class EmailLoginTests(TestCase):
    def test_email_is_normalized_lowercase(self):
        user = User.objects.create_user(
            username='u1', email='MiXeD@Example.COM', password='x', role='cliente')
        user.refresh_from_db()
        self.assertEqual(user.email, 'mixed@example.com')

    def test_login_by_email_case_insensitive(self):
        User.objects.create_user(
            username='u2', email='trainer@toptrack.com', password='secret123', role='admin')
        ok = self.client.login(username='TRAINER@toptrack.com', password='secret123')
        self.assertTrue(ok)

    def test_role_helpers(self):
        trainer = User.objects.create_user(
            username='t', email='t@t.com', password='x', role='admin')
        client_user = User.objects.create_user(
            username='c', email='c@c.com', password='x', role='cliente')
        self.assertTrue(trainer.is_trainer)
        self.assertFalse(trainer.is_client)
        self.assertTrue(client_user.is_client)
        self.assertFalse(client_user.is_trainer)


class ProfileAccessTests(TestCase):
    def test_profile_requires_login(self):
        resp = self.client.get(reverse('accounts:profile'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('accounts:login'), resp.url)

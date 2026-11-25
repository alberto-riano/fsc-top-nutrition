import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from clients.models import ClientProfile
from metrics.models import BodyMeasurement
from plans.models import Plan, Product

User = get_user_model()


class TrainerApiTests(TestCase):
    def setUp(self):
        trainer = User.objects.create_user(username='t', email='t@demo.com', password='x', role='admin')
        client_user = User.objects.create_user(username='c', email='c@demo.com', password='x', role='cliente')
        self.profile = ClientProfile.objects.create(user=client_user, profile_type='completo')
        self.trainer = APIClient()
        self.trainer.force_authenticate(trainer)
        self.client_api = APIClient()
        self.client_api.force_authenticate(client_user)

    def create_product(self, **extra):
        data = {'name': 'Whey Isolate', 'brand': 'Marca', 'url': 'https://example.com/whey', **extra}
        res = self.trainer.post('/api/v1/trainer/products/', data, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def test_client_cannot_manage_products(self):
        res = self.client_api.get('/api/v1/trainer/products/')
        self.assertEqual(res.status_code, 403)

    def test_product_url_must_be_http(self):
        res = self.trainer.post('/api/v1/trainer/products/', {'name': 'X', 'url': 'ftp://x.com'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_nutrition_plan_with_products_reaches_client(self):
        product = self.create_product()
        res = self.trainer.post(
            f'/api/v1/trainer/clients/{self.profile.pk}/plans/',
            {
                'plan_type': 'alimentacion',
                'title': 'Definición',
                'content': '',
                'products': json.dumps([{'product': product['id'], 'note': '1 cacito post-entreno'}]),
            },
            format='multipart',
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['products'][0]['note'], '1 cacito post-entreno')

        plans = self.client_api.get('/api/v1/plans/').json()
        self.assertEqual(plans[0]['products'][0]['url'], 'https://example.com/whey')

    def test_products_only_in_nutrition_plans(self):
        product = self.create_product()
        res = self.trainer.post(
            f'/api/v1/trainer/clients/{self.profile.pk}/plans/',
            {'plan_type': 'rutina', 'title': 'R', 'content': 'x',
             'products': json.dumps([{'product': product['id']}])},
            format='multipart',
        )
        self.assertEqual(res.status_code, 400)

    def test_deleting_used_product_archives_it(self):
        product = self.create_product()
        unused = self.create_product(name='Creatina')
        plan = Plan.objects.create(client=self.profile, plan_type='alimentacion', title='P', content='x')
        plan.plan_products.create(product_id=product['id'])

        res = self.trainer.delete(f"/api/v1/trainer/products/{product['id']}/")
        self.assertEqual(res.json(), {'archived': True})
        self.assertFalse(Product.objects.get(pk=product['id']).active)
        self.assertEqual(plan.plan_products.count(), 1)

        res = self.trainer.delete(f"/api/v1/trainer/products/{unused['id']}/")
        self.assertEqual(res.status_code, 204)
        listed = self.trainer.get('/api/v1/trainer/products/').json()
        self.assertEqual(listed, [])

    def test_trainer_records_body_composition(self):
        url = f'/api/v1/trainer/clients/{self.profile.pk}/metrics/body/'
        res = self.trainer.post(url, {'weight_kg': '72.5', 'body_fat_pct': '18.2',
                                      'muscle_mass_pct': '40.1', 'water_pct': '59.7'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(BodyMeasurement.objects.get().client, self.profile)

        res = self.trainer.post(url, {'weight_kg': '70', 'body_fat_pct': '60', 'muscle_mass_pct': '50'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_trainer_sets_client_sex(self):
        url = f'/api/v1/trainer/clients/{self.profile.pk}/'
        res = self.trainer.patch(url, {'sex': 'mujer', 'goal': 'no se toca'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['sex'], 'mujer')
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.goal, '')
        self.assertEqual(self.client_api.get('/api/v1/me/profile/').json()['sex'], 'mujer')
        self.assertEqual(self.trainer.patch(url, {'sex': 'otro'}, format='json').status_code, 400)

    def test_neck_is_no_longer_part_of_the_body_map(self):
        url = f'/api/v1/trainer/clients/{self.profile.pk}/metrics/circumference/'
        res = self.trainer.post(url, {'waist_cm': '80'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertNotIn('neck_cm', res.json())


class TrainerManagementTests(TestCase):
    """Bonos, marcas y altas de clientes desde la app del entrenador."""

    def setUp(self):
        trainer = User.objects.create_user(username='t', email='t@demo.com', password='x', role='admin')
        client_user = User.objects.create_user(
            username='c', email='c@demo.com', password='x', role='cliente', first_name='Ana', phone='600111222')
        self.profile = ClientProfile.objects.create(user=client_user, profile_type='completo')
        self.api = APIClient()
        self.api.force_authenticate(trainer)
        self.base = f'/api/v1/trainer/clients/{self.profile.pk}'

    # -- Bonos ---------------------------------------------------------------
    def test_renewing_before_running_out_queues_the_new_bono(self):
        from bonos.models import Bono, Session
        from django.utils import timezone
        old = Bono.objects.create(client=self.profile, sessions_total=2)
        Session.objects.create(bono=old, date=timezone.now())
        self.assertTrue(self.profile.low_sessions_alert)

        res = self.api.post(f'{self.base}/bonos/', {'bono_type': 'individual', 'sessions_total': 10,
                                                    'price': '300'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['sessions_left'], 11)
        self.assertEqual(res.json()['queued_sessions'], 10)

        profile = self.api.get(f'{self.base}/').json()
        self.assertEqual(profile['active_bono_id'], str(old.pk))
        self.assertFalse(profile['low_sessions_alert'])

        # La siguiente sesión sale del bono viejo.
        res = self.api.post(f'{self.base}/sessions/mark/', {}, format='json')
        self.assertEqual(res.json()['sessions_left'], 10)
        self.assertEqual(old.sessions_left, 0)

    def test_bono_validation(self):
        res = self.api.post(f'{self.base}/bonos/', {'sessions_total': 0}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.api.post(f'{self.base}/bonos/', {'sessions_total': 5, 'purchase_date': '2026-05-10',
                                                    'expiry_date': '2026-05-01'}, format='json')
        self.assertIn('expiry_date', res.json())

    # -- Marcas --------------------------------------------------------------
    def test_strength_records_detect_personal_best(self):
        catalog = self.api.get('/api/v1/trainer/catalog/').json()
        squat = catalog['exercises'][0]['id']
        first = self.api.post(f'{self.base}/metrics/strength/', {'exercise': squat, 'weight_kg': '100', 'reps': 5},
                              format='json').json()
        self.assertTrue(first['is_first'])
        worse = self.api.post(f'{self.base}/metrics/strength/', {'exercise': squat, 'weight_kg': '105', 'reps': 1},
                              format='json').json()
        self.assertFalse(worse['is_record'])  # 105×1 < 100×5 en 1RM estimado
        better = self.api.post(f'{self.base}/metrics/strength/', {'exercise': squat, 'weight_kg': '110', 'reps': 5},
                               format='json').json()
        self.assertTrue(better['is_record'])

    def test_new_exercise_by_name_is_reused(self):
        from metrics.models import Exercise
        for _ in range(2):
            res = self.api.post(f'{self.base}/metrics/strength/',
                                {'exercise_name': 'hip thrust', 'weight_kg': '80', 'reps': 8}, format='json')
            self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Exercise.objects.filter(name__iexact='hip thrust').count(), 1)
        self.assertEqual(res.json()['exercise_name'], 'Hip thrust')

    def test_endurance_lower_is_better(self):
        from metrics.models import EnduranceTestType
        sprint = EnduranceTestType.objects.create(name='Sprint 30 m', unit='segundos', lower_is_better=True)
        self.api.post(f'{self.base}/metrics/endurance/', {'test_type': sprint.pk, 'value': '4.8'}, format='json')
        res = self.api.post(f'{self.base}/metrics/endurance/', {'test_type': sprint.pk, 'value': '4.6'}, format='json')
        self.assertTrue(res.json()['is_record'])

    def test_future_dates_are_rejected(self):
        catalog = self.api.get('/api/v1/trainer/catalog/').json()
        res = self.api.post(f'{self.base}/metrics/strength/', {'exercise': catalog['exercises'][0]['id'],
                                                               'weight_kg': '50', 'reps': 5, 'date': '2999-01-01'},
                            format='json')
        self.assertEqual(res.status_code, 400)

    # -- Altas ---------------------------------------------------------------
    def test_create_client_with_invitation(self):
        res = self.api.post('/api/v1/trainer/clients/', {
            'first_name': 'Lucía', 'last_name': 'Pérez', 'username': 'Lucia.Perez', 'phone': '611 22 33 44',
            'profile_type': 'completo', 'sex': 'mujer',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body['username'], 'lucia.perez')
        self.assertTrue(body['access_pending'])
        self.assertIn('lucia.perez', body['invite']['message'])
        self.assertTrue(body['invite']['whatsapp_url'].startswith('https://wa.me/34611223344?text='))
        user = User.objects.get(email='lucia.perez')
        self.assertFalse(user.is_active)

        # El enlace de invitación funciona y activa la cuenta.
        path = body['invite']['url'].split('testserver')[1]
        page = self.client.get(path)
        self.assertContains(page, 'lucia.perez')
        self.client.post(path, {'new_password1': 'Entrena-2026!', 'new_password2': 'Entrena-2026!'})
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_create_client_with_password_has_no_invite(self):
        res = self.api.post('/api/v1/trainer/clients/', {
            'first_name': 'Pablo', 'username': 'pablo', 'password': 'Entrena-2026!',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertIsNone(res.json()['invite'])
        self.assertFalse(res.json()['access_pending'])

    def test_create_client_validation(self):
        res = self.api.post('/api/v1/trainer/clients/', {'first_name': 'X', 'username': 'C@demo.com'}, format='json')
        self.assertIn('username', res.json())
        res = self.api.post('/api/v1/trainer/clients/', {'first_name': 'Leo', 'username': 'leo',
                                                         'profile_type': 'futbolista'}, format='json')
        self.assertIn('birth_date', res.json())
        self.assertIn('guardian_name', res.json())

    def test_username_check_suggests_next_free(self):
        res = self.api.get('/api/v1/trainer/usernames/check/', {'username': 'c@demo.com'}).json()
        self.assertEqual(res, {'available': False, 'suggestion': 'c@demo.com2'})
        res = self.api.get('/api/v1/trainer/usernames/check/', {'username': 'nuevo'}).json()
        self.assertTrue(res['available'])

    def test_resend_invite(self):
        res = self.api.post(f'{self.base}/invite/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['access_pending'])
        self.assertIn('Ana', res.json()['message'])

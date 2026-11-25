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

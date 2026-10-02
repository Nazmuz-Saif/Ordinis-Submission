from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from core.test_utils import register_company
from rbac.models import Permission
from tenants.models import Company


class RegistrationAndMeTests(TestCase):
    def test_registration_gives_ceo_full_permissions(self):
        ceo = register_company('Acme', 'acme', 'ceo@acme.com')
        me = ceo.get('/api/v1/auth/me/').data['data']
        self.assertEqual(set(me['permissions']), set(Permission.objects.values_list('codename', flat=True)))
        self.assertTrue(me['permissions'])

    def test_user_without_company_is_never_attached_to_a_company(self):
        register_company('Acme', 'acme', 'ceo@acme.com')
        orphan = User.objects.create_user(email='orphan@x.com', password='StrongPass123')
        client = APIClient()
        client.force_authenticate(orphan)

        me = client.get('/api/v1/auth/me/').data['data']
        self.assertIsNone(me['company_id'])
        self.assertEqual(me['permissions'], [])

        self.assertEqual(client.get('/api/v1/organization/departments/').status_code, 403)
        self.assertEqual(client.get('/api/v1/rbac/roles/').status_code, 403)

        orphan.refresh_from_db()
        self.assertIsNone(orphan.company)
        self.assertEqual(Company.objects.count(), 1)


class TokenLifecycleTests(TestCase):
    def setUp(self):
        register_company('Acme', 'acme', 'ceo@acme.com')
        self.client = APIClient()
        res = self.client.post('/api/v1/auth/login/', {'email': 'ceo@acme.com', 'password': 'StrongPass123'}, format='json')
        self.access, self.refresh = res.data['access'], res.data['refresh']

    def test_access_token_lives_15_minutes_and_refresh_rotates(self):
        from datetime import timedelta
        from rest_framework_simplejwt.settings import api_settings
        self.assertEqual(api_settings.ACCESS_TOKEN_LIFETIME, timedelta(minutes=15))
        self.assertTrue(api_settings.ROTATE_REFRESH_TOKENS)

        res = self.client.post('/api/v1/auth/refresh/', {'refresh': self.refresh}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertNotEqual(res.data['refresh'], self.refresh)

    def test_a_used_refresh_token_cannot_be_used_again(self):
        self.client.post('/api/v1/auth/refresh/', {'refresh': self.refresh}, format='json')
        again = self.client.post('/api/v1/auth/refresh/', {'refresh': self.refresh}, format='json')
        self.assertEqual(again.status_code, 401)

    def test_logout_blacklists_the_refresh_token(self):
        out = self.client.post('/api/v1/auth/logout/', {'refresh': self.refresh}, format='json')
        self.assertEqual(out.status_code, 200)
        res = self.client.post('/api/v1/auth/refresh/', {'refresh': self.refresh}, format='json')
        self.assertEqual(res.status_code, 401)

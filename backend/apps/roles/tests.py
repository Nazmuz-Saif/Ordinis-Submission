from rest_framework import status
from rest_framework.test import APITestCase
from tenants.models import Company
from accounts.models import User
from roles.models import Role, Permission


class RoleAPITestCase(APITestCase):
    """
    Self-test suite for Role creation, retrieval, and company-level scoping (ST-110).
    Verifies that:
      1. Authenticated users can list permissions.
      2. Roles can be created with assigned permissions.
      3. Company A user can only see Company A's roles (scoping).
      4. Company B user can only see Company B's roles (isolation).
    """

    def setUp(self):
        # Company A & User A
        self.company_a = Company.objects.create(
            name="Alpha Corp", subdomain="alpha-corp"
        )
        self.user_a = User.objects.create_user(
            email="admin@alpha.com", password="password123", company=self.company_a
        )

        # Company B & User B
        self.company_b = Company.objects.create(
            name="Beta Ltd", subdomain="beta-ltd"
        )
        self.user_b = User.objects.create_user(
            email="admin@beta.com", password="password123", company=self.company_b
        )

        # Ensure permissions exist (from seed or created here)
        self.perm1, _ = Permission.objects.get_or_create(
            codename="manage_departments",
            defaults={"name": "Manage Departments", "module": "organization"},
        )
        self.perm2, _ = Permission.objects.get_or_create(
            codename="manage_employees",
            defaults={"name": "Manage Employees", "module": "organization"},
        )

        # Pre-create a role for Company A
        self.role_a = Role.objects.create(
            company=self.company_a, name="Alpha Manager", description="Alpha manager role"
        )
        self.role_a.permissions.add(self.perm1)

        # Pre-create a role for Company B
        self.role_b = Role.objects.create(
            company=self.company_b, name="Beta Auditor", description="Beta auditor role"
        )
        self.role_b.permissions.add(self.perm2)

        self.roles_url = "/api/v1/roles/roles/"
        self.permissions_url = "/api/v1/roles/permissions/"

    def test_list_permissions_authenticated(self):
        """Test retrieving system permissions list (Read-Only)"""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.permissions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_create_role_with_permissions(self):
        """Test creating a new role with assigned permissions under user's company"""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            "name": "Alpha HR Lead",
            "description": "Handles Alpha HR",
            "permissions": [str(self.perm1.id), str(self.perm2.id)],
        }
        response = self.client.post(self.roles_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Alpha HR Lead")

        # Verify saved in DB scoped to company_a
        created_role = Role.objects.get(id=response.data["id"])
        self.assertEqual(created_role.company, self.company_a)
        self.assertEqual(created_role.permissions.count(), 2)

    def test_company_level_scoping_company_a(self):
        """Company A user only sees Company A roles (Alpha Manager), not Company B roles"""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(self.roles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        role_names = [r["name"] for r in response.data]
        self.assertIn("Alpha Manager", role_names)
        self.assertNotIn("Beta Auditor", role_names)

    def test_company_level_scoping_company_b(self):
        """Company B user only sees Company B roles (Beta Auditor), not Company A roles"""
        self.client.force_authenticate(user=self.user_b)
        response = self.client.get(self.roles_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        role_names = [r["name"] for r in response.data]
        self.assertIn("Beta Auditor", role_names)
        self.assertNotIn("Alpha Manager", role_names)

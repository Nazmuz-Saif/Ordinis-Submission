from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from tenants.models import Company
from organization.models import Employee
from .models import Attendance


class AttendanceTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.company = Company.objects.create(
            name='Test Company',
            subdomain='test-company',
            industry='Software',
        )

        self.user = User.objects.create_user(
            email='employee@test.com',
            password='TestPass123',
            company=self.company,
        )

        self.employee = Employee.objects.create(
            user=self.user,
            company=self.company,
            employee_code='EMP-001',
        )

        self.client.force_authenticate(user=self.user)

    def test_check_in(self):
        response = self.client.post(
            '/api/v1/attendance/attendance/check-in/'
        )

        self.assertEqual(response.status_code, 200)

        attendance = Attendance.objects.get(
            employee=self.employee,
            date=timezone.localdate(),
        )

        self.assertIsNotNone(attendance.check_in)
        self.assertIsNone(attendance.check_out)

    def test_duplicate_check_in_is_blocked(self):
        self.client.post(
            '/api/v1/attendance/attendance/check-in/'
        )

        response = self.client.post(
            '/api/v1/attendance/attendance/check-in/'
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).count(),
            1,
        )

    def test_checkout_before_checkin_is_blocked(self):
        response = self.client.post(
            '/api/v1/attendance/attendance/check-out/'
        )

        self.assertEqual(response.status_code, 400)

        self.assertFalse(
            Attendance.objects.filter(
                employee=self.employee,
                date=timezone.localdate(),
            ).exists()
        )

    def test_check_out_after_check_in(self):
        self.client.post(
            '/api/v1/attendance/attendance/check-in/'
        )

        response = self.client.post(
            '/api/v1/attendance/attendance/check-out/'
        )

        self.assertEqual(response.status_code, 200)

        attendance = Attendance.objects.get(
            employee=self.employee,
            date=timezone.localdate(),
        )

        self.assertIsNotNone(attendance.check_in)
        self.assertIsNotNone(attendance.check_out)

    def test_today_attendance_list(self):
        response = self.client.get(
            '/api/v1/attendance/attendance/'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]['employee_code'],
            'EMP-001',
        )

        self.assertIsNone(
            response.data[0]['check_in']
        )

        self.assertIsNone(
            response.data[0]['check_out']
        )
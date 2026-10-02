from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Employee
from rbac.models import Permission, Role


def register_company(name, subdomain, email):
    """Registers a company through the real endpoint. Returns an APIClient logged in as its CEO."""
    client = APIClient()
    res = client.post('/api/v1/auth/register/', {
        'company_name': name,
        'subdomain': subdomain,
        'ceo_email': email,
        'ceo_password': 'StrongPass123',
    }, format='json')
    assert res.status_code == 201, res.content
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['data']['access'])
    client.company_id = res.data['data']['company_id']
    client.employee_id = res.data['data']['employee_id']
    return client


def login_as(email, password='StrongPass123'):
    client = APIClient()
    res = client.post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')
    assert res.status_code == 200, res.content
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + res.data['access'])
    return client


def add_employee(ceo_client, email, code, **extra):
    """Creates an employee (no roles) through the API as the CEO."""
    payload = {'email': email, 'password': 'StrongPass123', 'employee_code': code, **extra}
    res = ceo_client.post('/api/v1/organization/employees/', payload, format='json')
    assert res.status_code == 201, res.content
    return res.data


def give_role(company_id, employee_id, codenames, role_name='Custom'):
    """Creates a Role with the given Permission codenames and assigns it (direct DB helper)."""
    from rbac.models import EmployeeRole
    employee = Employee.objects.get(id=employee_id)
    role = Role.objects.create(company_id=company_id, name=role_name)
    role.permissions.set(Permission.objects.filter(codename__in=codenames))
    EmployeeRole.objects.create(employee=employee, role=role, company_id=company_id)
    return role

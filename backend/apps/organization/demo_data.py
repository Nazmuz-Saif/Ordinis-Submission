from accounts.models import User
from core import demo
from .models import Department, Designation, Employee

ORDER = 10


def seed(ctx):
    company = ctx.company
    departments = {}
    for name in demo.DEPARTMENTS:
        obj, created = Department.objects.get_or_create(company=company, name=name)
        ctx.note('departments', created)
        departments[name] = obj

    for index, (key, local, title, department, _boss, _roles) in enumerate(demo.PEOPLE, start=1):
        designation, created = Designation.objects.get_or_create(company=company, title=title)
        ctx.note('designations', created)
        if key == 'ceo':   # made by company registration
            employee = Employee.objects.get(company=company, user__email=demo.email(local))
        else:
            user = User.objects.filter(email=demo.email(local)).first()
            if user is None:
                user = User.objects.create_user(email=demo.email(local), password=demo.PASSWORD, company=company)
            employee, created = Employee.objects.get_or_create(
                user=user, defaults={'company': company, 'employee_code': f'DEMO-EMP{index:03d}'},
            )
            ctx.note('employees', created)
        employee.department = departments[department]
        employee.designation = designation
        employee.save(update_fields=['department', 'designation', 'updated_at'])
        ctx.employees[key] = employee

    for key, _local, _title, _department, boss, _roles in demo.PEOPLE:   # the multi-level hierarchy
        if boss:
            employee = ctx.emp(key)
            if employee.reports_to_id != ctx.emp(boss).id:
                employee.reports_to = ctx.emp(boss)
                employee.save(update_fields=['reports_to', 'updated_at'])

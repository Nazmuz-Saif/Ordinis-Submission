from .models import Employee


def get_all_subordinates(employee: Employee):
    
    subordinates = []
    direct_reports = employee.direct_reports.all()

    for report in direct_reports:
        subordinates.append(report)
        subordinates.extend(get_all_subordinates(report))

    return subordinates


def get_all_managers(employee: Employee):
    
    managers = []
    current = employee.reports_to

    while current is not None:
        managers.append(current)
        current = current.reports_to

    return managers


def can_view_employee_data(viewer: Employee, target: Employee) -> bool:
    
    if viewer.id == target.id:
        return True

    subordinates = get_all_subordinates(viewer)
    return target in subordinates
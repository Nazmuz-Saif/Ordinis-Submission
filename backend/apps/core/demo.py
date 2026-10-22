"""
Demo data: the ONE place that defines the demo company, its people and its logins, and how seeders are found.

How to add demo data for a new app: create `<app>/demo_data.py` with
    ORDER = 70            # lower runs first (see the ORDER list in each app's demo_data.py)
    def seed(ctx): ...    # use get_or_create so running it twice never duplicates anything
    def wipe(company): ...   # OPTIONAL, only if the app has PROTECT links that block deleting the company
Nothing else changes: `seed_demo_data` finds the file by itself.
"""
import importlib
from collections import Counter

from django.apps import apps as django_apps

SUBDOMAIN = 'demo-acme'
COMPANY_NAME = 'Acme Technologies Ltd.'
INDUSTRY = 'Software'
DOMAIN = 'demo.ordinis.test'
PASSWORD = 'Demo@12345'


def email(local):
    return f'{local}@{DOMAIN}'


# key, email name, designation, department, reports to (key), Role names.
# Ten people on purpose: the Basic plan (10 employees) must still have room for the demo company.
PEOPLE = [
    ('ceo', 'ceo', 'CEO', 'Management', None, []),   # created by company registration (it holds the CEO role)
    ('gm', 'nusrat.jahan', 'General Manager', 'Management', 'ceo', []),
    ('manager', 'manager', 'Engineering Manager', 'Engineering', 'gm', ['Manager']),
    ('sales_head', 'imran.hossain', 'Sales Manager', 'Sales', 'gm', ['Manager']),
    ('hr', 'hr', 'HR Executive', 'Human Resources', 'gm', ['HR']),
    ('accountant', 'accountant', 'Accountant', 'Finance', 'ceo', ['Accountant']),
    ('employee', 'employee', 'Software Engineer', 'Engineering', 'manager', []),
    ('dev2', 'farhan.ahmed', 'Software Engineer', 'Engineering', 'manager', []),
    ('designer', 'mehedi.hasan', 'UI Designer', 'Engineering', 'manager', []),
    ('sales1', 'rafiq.islam', 'Sales Executive', 'Sales', 'sales_head', []),
]
# Real names for the demo people, by the email name above. Shown first on every page.
NAMES = {
    'ceo': 'Reza Chowdhury',
    'nusrat.jahan': 'Nusrat Jahan',
    'manager': 'Tanvir Rahman',
    'imran.hossain': 'Imran Hossain',
    'hr': 'Sadia Karim',
    'accountant': 'Mahbub Alam',
    'employee': 'Ayesha Siddiqua',
    'farhan.ahmed': 'Farhan Ahmed',
    'mehedi.hasan': 'Mehedi Hasan',
    'rafiq.islam': 'Rafiq Islam',
    'platform': 'Ordinis Support',
}


def name(local):
    return NAMES[local]


DEPARTMENTS = ['Management', 'Engineering', 'Sales', 'Human Resources', 'Finance']

# The Platform Admin (company-less). It is not part of the demo company, so --reset and --delete keep it.
PLATFORM_LOGIN = ('Platform Admin', 'platform')

# One login per dashboard, shown at the end of the command.
LOGINS = [('CEO', 'ceo'), ('Manager', 'manager'), ('HR', 'hr'), ('Accountant', 'accountant'), ('Employee', 'employee')]


class DemoContext:
    """What every seeder gets: the company, the employees by key, today, and a counter of what was created."""

    def __init__(self, company):
        from attendance.services import local_today
        self.company = company
        self.employees = {}
        self.today, self.zone = local_today(company)
        self.created = Counter()

    def emp(self, key):
        return self.employees[key]

    def note(self, label, created):
        if created:
            self.created[label] += 1
        return created


def _demo_modules():
    for config in django_apps.get_app_configs():
        try:
            yield config.name, importlib.import_module(f'{config.name}.demo_data')
        except ModuleNotFoundError as exc:
            if exc.name != f'{config.name}.demo_data':
                raise


def discover_seeders():
    """[(ORDER, app name, seed function)] for every installed app that has a demo_data module."""
    found = [(module.ORDER, name, module.seed) for name, module in _demo_modules()]
    return sorted(found, key=lambda item: (item[0], item[1]))


def discover_wipers():
    """
    [(app name, wipe function)], last seeder first. An app adds `wipe(company)` to its demo_data.py only when
    something of its own stops the company from being deleted (a PROTECT link); it removes just that.
    """
    found = [(module.ORDER, name, module.wipe) for name, module in _demo_modules() if hasattr(module, 'wipe')]
    return [(name, fn) for _order, name, fn in sorted(found, key=lambda item: (item[0], item[1]), reverse=True)]

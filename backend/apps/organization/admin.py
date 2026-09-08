from django.contrib import admin
from .models import Department, Designation, Employee

admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(Employee)
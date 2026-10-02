from django.contrib import admin
from .models import EmployeeRole, Permission, Role

admin.site.register(Permission)
admin.site.register(Role)

admin.site.register(EmployeeRole)

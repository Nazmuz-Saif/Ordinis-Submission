from django.contrib import admin
from .models import Permission, Role, EmployeeRole

admin.site.register(Permission)
admin.site.register(Role)
admin.site.register(EmployeeRole)

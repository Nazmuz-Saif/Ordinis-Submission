from django.contrib import admin

from .models import ApprovalChain, ApprovalStep

admin.site.register(ApprovalChain)
admin.site.register(ApprovalStep)

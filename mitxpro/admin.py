"""Django admin functionality that is relevant to the entire app"""
from django.contrib import admin


class AuditableModelAdmin(admin.ModelAdmin):
    """A ModelAdmin which will save and log"""

    def save_model(self, request, obj, form, change):
        obj.save_and_log(request.user)

"""
Admin site bindings for sheets models
"""

from django.contrib import admin

from sheets import models


class ServiceAccountCredentialsAdmin(admin.ModelAdmin):
    """Admin for ServiceAccountCredentials"""

    model = models.ServiceAccountCredentials

    list_display = ("id", "value")


admin.site.register(models.ServiceAccountCredentials, ServiceAccountCredentialsAdmin)

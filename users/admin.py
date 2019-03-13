"""User admin"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as ContribUserAdmin
from django.utils.translation import gettext_lazy as _
from hijack_admin.admin import HijackUserAdminMixin

from users.models import User


class UserAdmin(ContribUserAdmin, HijackUserAdminMixin):
    """Admin views for user"""

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    list_display = ("username", "email", "name", "is_staff", "hijack_field")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "name", "email")
    ordering = ("email",)
    readonly_fields = ("username",)


admin.site.register(User, UserAdmin)

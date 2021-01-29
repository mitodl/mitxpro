"""User admin"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as ContribUserAdmin
from django.utils.translation import gettext_lazy as _
from hijack_admin.admin import HijackUserAdminMixin

from mitxpro.admin import TimestampedModelAdmin
from users.models import LegalAddress, User, Profile


class UserLegalAddressInline(admin.StackedInline):
    """Admin view for the legal address"""

    model = LegalAddress
    classes = ["collapse"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("first_name", "last_name"),
                    "street_address_1",
                    "street_address_2",
                    "street_address_3",
                    "street_address_4",
                    "street_address_5",
                    ("city", "state_or_territory", "postal_code"),
                    "country",
                )
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        return False


class UserProfileInline(admin.StackedInline):
    """Admin view for the profile"""

    model = Profile
    classes = ["collapse"]

    def has_delete_permission(self, request, obj=None):
        return True


_username_warning = """
<div style="background-color: #dc3545; color: #fff; padding: 10px; font-size: 16px; border-radius: 5px;">
   <strong>WARNING:</strong> 
   Changing this username will require you to apply the same change in edX immediately after.<br /><br>
   Do not make this change unless you can perform the same change to the edX username, or you have someone
   else lined up to do it.
</div>
"""


class UserAdmin(ContribUserAdmin, HijackUserAdminMixin, TimestampedModelAdmin):
    """Admin views for user"""

    include_created_on_in_list = True
    fieldsets = (
        (None, {"fields": ("password", "last_login", "created_on")}),
        (_("Username"), {"fields": ("username",), "description": _username_warning}),
        (_("Personal Info"), {"fields": ("name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ["collapse"],
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "name",
        "is_staff",
        "hijack_field",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "name", "email")
    ordering = ("email",)
    readonly_fields = ("last_login",)
    inlines = [UserLegalAddressInline, UserProfileInline]


admin.site.register(User, UserAdmin)

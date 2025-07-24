"""
Custom permissions for the CMS app.
"""

from rest_framework.permissions import BasePermission

from cms.constants import CMS_GROUP_EDITORS, CMS_GROUP_MODERATORS


class IsCmsStaffOrSuperuser(BasePermission):
    """
    Allows access only to superusers, or staff users who are in either
    the editors or moderators group.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if user.is_staff:
            user_groups = set(user.groups.values_list("name", flat=True))
            return bool({CMS_GROUP_EDITORS, CMS_GROUP_MODERATORS} & user_groups)
        return False

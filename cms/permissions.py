"""
Custom permissions for the CMS app.
"""

from rest_framework.permissions import BasePermission

from cms.constants import EDITORS_GROUP_NAME, MODERATORS_GROUP_NAME


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
            return user.groups.filter(
                name__in=[EDITORS_GROUP_NAME, MODERATORS_GROUP_NAME]
            ).exists()
        return False

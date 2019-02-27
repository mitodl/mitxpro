"""Custom permissions"""
from rest_framework import permissions


class UserIsOwnerPermission(permissions.BasePermission):
    """Determines if the user owns the object"""

    def has_object_permission(self, request, view, obj):
        """
        Returns True if the requesting user is the owner of the object as
        determined by the "owner_field" property on the view (defaults to "user")
        """
        owner_field = getattr(view, "owner_field", None)

        if owner_field is None:
            # if no owner_field is specified, the object itself is compared
            owner = obj
        else:
            # otherwise we lookup the owner by the specified field
            owner = getattr(obj, owner_field)

        return owner == request.user

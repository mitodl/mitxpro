
from rest_framework.permissions import BasePermission

from sheets.constants import COUPON_PRODUCT_ASSIGNMENT_ADD_PERMISSION, COUPON_PRODUCT_ASSIGNMENT_UPDATE_PERMISSION

class HasCouponProductAssignmentPermission(BasePermission):
    """
    Custom permission to check if the user has both add and update permissions
    for coupon product assignments.
    """

    def has_permission(self, request, view):  # noqa: ARG002
        return (
            all(
                request.user.has_perm(perm)
                for perm in [
                    COUPON_PRODUCT_ASSIGNMENT_ADD_PERMISSION,
                    COUPON_PRODUCT_ASSIGNMENT_UPDATE_PERMISSION,
                ]
            )
        )
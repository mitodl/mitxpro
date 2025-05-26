"""Permission classes for ecommerce"""

import logging

from rest_framework.permissions import BasePermission

from ecommerce.api import generate_cybersource_sa_signature
from ecommerce.constants import COUPON_ADD_PERMISSION, COUPON_UPDATE_PERMISSION

log = logging.getLogger(__name__)


class IsSignedByCyberSource(BasePermission):
    """
    Confirms that the message is signed by CyberSource
    """

    def has_permission(self, request, view):  # noqa: ARG002
        """
        Returns true if request params are signed by CyberSource
        """
        signature = generate_cybersource_sa_signature(request.data)
        if request.data["signature"] == signature:
            return True
        else:
            log.error(
                "Cybersource signature failed: we expected %s but we got %s. Payload: %s",
                signature,
                request.data["signature"],
                request.data,
            )
            return False


class HasCouponPermission(BasePermission):
    """
    Custom permission to check if the user has the correct coupon permissions based on the HTTP method.
    """

    def has_permission(self, request, view):  # noqa: ARG002
        if request.method == "POST":
            return request.user.has_perm(COUPON_ADD_PERMISSION)

        if request.method in ["PUT", "GET"]:
            return request.user.has_perm(COUPON_UPDATE_PERMISSION)

        return False

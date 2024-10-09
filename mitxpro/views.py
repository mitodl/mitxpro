"""
mitxpro views
"""

import json

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework.views import APIView

from mitxpro.serializers import AppContextSerializer


def get_base_context(request):  # noqa: ARG001
    """
    Returns the template context key/values needed for the base template and all templates that extend it
    """
    context = {}
    if settings.GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE:
        context["domain_verification_tag"] = (
            settings.GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE
        )
    context["support_email"] = settings.EMAIL_SUPPORT
    return context


@csrf_exempt
def index(request, **kwargs):  # noqa: ARG001
    """
    The index view
    """
    context = get_base_context(request)

    if request.method == "POST" and (
        "auth_amount" in request.POST
        and "req_merchant_defined_data2" in request.POST
        and "req_merchant_defined_data1" in request.POST
        and "req_reference_number" in request.POST
        and "req_transaction_uuid" in request.POST
        and "reason_code" in request.POST
        and request.POST["reason_code"] == "100"
    ):
        payment_dict = {
            "transaction_id": request.POST["req_transaction_uuid"],
            "transaction_total": float(request.POST["auth_amount"]),
            "reference_number": request.POST["req_reference_number"],
            "product_type": request.POST["req_merchant_defined_data1"],
            "courseware_id": request.POST["req_merchant_defined_data2"],
        }

        # Inject the cybersource POST payload into the context so
        # that it can be processed for purchase tracking on the front
        # end via GTM
        context["CSOURCE_PAYLOAD"] = json.dumps(payment_dict)

    return render(request, "index.html", context=context)


def handler404(request, exception):  # noqa: ARG001
    """404: NOT FOUND ERROR handler"""
    response = render_to_string(
        "404.html", request=request, context=get_base_context(request)
    )
    return HttpResponseNotFound(response)


def handler500(request):
    """500 INTERNAL SERVER ERROR handler"""
    response = render_to_string(
        "500.html", request=request, context=get_base_context(request)
    )
    return HttpResponseServerError(response)


def cms_signin_redirect_to_site_signin(request):  # noqa: ARG001
    """Redirect wagtail admin signin to site signin page"""
    return redirect_to_login(reverse("wagtailadmin_home"), login_url="/signin")


def ecommerce_restricted(request):
    """
    Views restricted to admins
    """
    has_coupon_create_permission = request.user.has_perm("ecommerce.add_coupon")
    has_coupon_update_permission = request.user.has_perm("ecommerce.change_coupon")

    if not (request.user and (has_coupon_create_permission or has_coupon_update_permission)):
        raise PermissionDenied

    if request.path.startswith("/ecommerce/admin/coupons") and not has_coupon_create_permission or request.path.startswith("/ecommerce/admin/deactivate-coupons") and not has_coupon_update_permission:
        raise PermissionDenied

    context = get_base_context(request)
    context["user_permissions"] = json.dumps({
        "has_coupon_create_permission": has_coupon_create_permission,
        "has_coupon_update_permission": has_coupon_update_permission,
    })
    return render(request, "index.html", context=context)


class AppContextView(APIView):
    """Renders the user context as JSON"""

    permission_classes = []

    def get(self, request, *args, **kwargs):  # noqa: ARG002
        """Read-only access"""
        return Response(AppContextSerializer(request).data)

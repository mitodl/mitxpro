"""
mitxpro views
"""
import os
import json

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotFound, HttpResponseServerError
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from rest_framework.views import APIView
from rest_framework.response import Response

from mitxpro.serializers import AppContextSerializer
from mitxpro.templatetags.render_bundle import public_path
from mitxpro.utils import remove_password_from_url


def get_base_context(request):
    """
    Returns the template context key/values needed for the base template and all templates that extend it
    """
    context = {
        "js_settings_json": json.dumps(
            {
                "gaTrackingID": settings.GA_TRACKING_ID,
                "environment": settings.ENVIRONMENT,
                "public_path": public_path(request),
                "release_version": settings.VERSION,
                "recaptchaKey": settings.RECAPTCHA_SITE_KEY,
                "sentry_dsn": remove_password_from_url(
                    os.environ.get("SENTRY_DSN", "")
                ),
                "support_email": settings.EMAIL_SUPPORT,
                "site_name": settings.SITE_NAME,
            }
        )
    }
    if settings.GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE:
        context[
            "domain_verification_tag"
        ] = settings.GOOGLE_DOMAIN_VERIFICATION_TAG_VALUE
    return context


@csrf_exempt
def index(request, **kwargs):  # pylint: disable=unused-argument
    """
    The index view
    """
    if request.method == "GET":
        return render(request, "index.html", context=get_base_context(request))
    else:
        return redirect(request.get_full_path())


def handler404(request, exception):
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


def cms_signin_redirect_to_site_signin(request):
    """Redirect wagtail admin signin to site signin page"""
    return redirect_to_login(reverse("wagtailadmin_home"), login_url="/signin")


def restricted(request):
    """
    Views restricted to admins
    """
    if not (request.user and request.user.is_staff):
        raise PermissionDenied
    return render(request, "index.html", context=get_base_context(request))


class AppContextView(APIView):
    """Renders the user context as JSON"""

    permission_classes = []

    def get(self, request, *args, **kwargs):
        """Read-only access"""
        return Response(AppContextSerializer(request).data)

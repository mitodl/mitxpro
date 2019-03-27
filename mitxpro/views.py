"""
mitxpro views
"""
import json

from django.conf import settings
from django.shortcuts import render
from raven.contrib.django.raven_compat.models import client as sentry
from rest_framework.views import APIView
from rest_framework.response import Response

from mitxpro.serializers import AppContextSerializer
from mitxpro.templatetags.render_bundle import public_path


def get_js_settings_context(request):
    """
    Returns the template context key/value needed for templates that render
    JS settings as JSON.
    """
    js_settings = {
        "gaTrackingID": settings.GA_TRACKING_ID,
        "environment": settings.ENVIRONMENT,
        "public_path": public_path(request),
        "release_version": settings.VERSION,
        "sentry_dsn": sentry.get_public_dsn(),
    }
    return {"js_settings_json": json.dumps(js_settings)}


def index(request):
    """
    The index view
    """
    return render(request, "index.html", context=get_js_settings_context(request))


class AppContextView(APIView):
    """Renders the user context as JSON"""

    permission_classes = []

    def get(self, request, *args, **kwargs):
        """Read-only access"""
        return Response(AppContextSerializer(request).data)

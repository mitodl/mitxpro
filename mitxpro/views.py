"""
mitxpro views
"""
import json

from django.conf import settings
from django.shortcuts import render
from raven.contrib.django.raven_compat.models import client as sentry

from mitxpro.templatetags.render_bundle import public_path


def index(request):
    """
    The index view. Display available programs
    """

    js_settings = {
        "gaTrackingID": settings.GA_TRACKING_ID,
        "environment": settings.ENVIRONMENT,
        "public_path": public_path(request),
        "release_version": settings.VERSION,
        "sentry_dsn": sentry.get_public_dsn(),
    }

    return render(
        request, "index.html", context={"js_settings_json": json.dumps(js_settings)}
    )

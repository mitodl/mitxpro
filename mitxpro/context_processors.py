"""
context processors for bootcamp
"""

from django.conf import settings


def api_keys(request):  # noqa: ARG001
    """
    Pass a `APIKEYS` dictionary into the template context, which holds
    IDs and secret keys for the various APIs used in this project.
    """
    return {
        "APIKEYS": {
            "GA_TRACKING_ID": settings.GA_TRACKING_ID,
            "GTM_TRACKING_ID": settings.GTM_TRACKING_ID,
        }
    }


def configuration_context(request):  # noqa: ARG001
    """
    Configuration context for django templates.
    """
    return {
        "hubspot_portal_id": settings.HUBSPOT_CONFIG.get("HUBSPOT_PORTAL_ID"),
        "hubspot_new_courses_form_guid": settings.HUBSPOT_CONFIG.get(
            "HUBSPOT_NEW_COURSES_FORM_GUID"
        ),
        "hubspot_footer_form_guid": settings.HUBSPOT_CONFIG.get(
            "HUBSPOT_FOOTER_FORM_GUID"
        ),
        "site_name": settings.SITE_NAME,
    }

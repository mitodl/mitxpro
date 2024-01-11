"""Templatetags for rendering site notification"""

from django import template

from cms.models import SiteNotification

register = template.Library()


@register.inclusion_tag("../templates/partials/notifications.html", takes_context=True)
def latest_notification(context):
    """Return request context and latest notification."""

    return {
        "notification": SiteNotification.objects.order_by("-id").first(),
        "request": context["request"],
    }

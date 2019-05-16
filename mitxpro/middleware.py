"""Banner notification middleware"""
from django.utils.deprecation import MiddlewareMixin

from cms.models import NotificationPage


class BannerNotificationMiddleware(MiddlewareMixin):
    """
    Middleware for settings site-wide notification in sessions
    """

    def process_request(self, request):
        """
        Get all live notifications and set them in session.
        """
        request.session["notifications"] = [
            n.notification for n in NotificationPage.objects.live()
        ]

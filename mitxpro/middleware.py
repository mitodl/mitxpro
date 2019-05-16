"""Authentication middleware"""
from django.shortcuts import redirect
from django.utils.http import urlquote
from django.utils.deprecation import MiddlewareMixin

from social_core.exceptions import SocialAuthBaseException
from social_django.middleware import SocialAuthExceptionMiddleware

from cms.models import NotificationPage


class SocialAuthExceptionRedirectMiddleware(SocialAuthExceptionMiddleware):
    """
    This middleware subclasses SocialAuthExceptionMiddleware and overrides
    process_exception to provide an implementation that does not use
    django.contrib.messages and instead only issues a redirect
    """

    def process_exception(self, request, exception):
        """
        Note: this is a subset of the SocialAuthExceptionMiddleware implementation
        """
        strategy = getattr(request, "social_strategy", None)
        if strategy is None or self.raise_exception(request, exception):
            return

        if isinstance(exception, SocialAuthBaseException):
            backend = getattr(request, "backend", None)
            backend_name = getattr(backend, "name", "unknown-backend")

            message = self.get_message(request, exception)
            url = self.get_redirect_uri(request, exception)

            if url:
                url += ("?" in url and "&" or "?") + "message={0}&backend={1}".format(
                    urlquote(message), backend_name
                )
                return redirect(url)


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

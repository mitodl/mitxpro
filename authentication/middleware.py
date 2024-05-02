"""Authentication middleware"""

from urllib.parse import quote

from django.shortcuts import redirect
from social_core.exceptions import SocialAuthBaseException
from social_django.middleware import SocialAuthExceptionMiddleware


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
            return  # noqa: RET502

        if isinstance(exception, SocialAuthBaseException):  # noqa: RET503
            backend = getattr(request, "backend", None)
            backend_name = getattr(backend, "name", "unknown-backend")

            message = self.get_message(request, exception)
            url = self.get_redirect_uri(request, exception)

            if url:  # noqa: RET503
                url += ("?" in url and "&" or "?") + "message={0}&backend={1}".format(  # noqa: UP030
                    quote(message), backend_name
                )
                return redirect(url)

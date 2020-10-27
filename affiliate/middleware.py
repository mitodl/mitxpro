"""Middleware for affiliate tracking"""
from affiliate.api import get_affiliate_code_from_qstring
from affiliate.constants import AFFILIATE_CODE_SESSION_KEY


class AffiliateMiddleware:
    """Middleware that adds an affiliate code to the request object if one is found in the querystring or the session"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.affiliate_code = None
        session = getattr(request, "session")
        if session is None:
            return self.get_response(request)
        qs_affiliate_code = get_affiliate_code_from_qstring(request)
        if qs_affiliate_code is not None:
            session[AFFILIATE_CODE_SESSION_KEY] = qs_affiliate_code
        request.affiliate_code = session.get(AFFILIATE_CODE_SESSION_KEY)
        return self.get_response(request)

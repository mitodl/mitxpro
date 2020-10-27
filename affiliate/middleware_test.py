"""Affiliate middleware tests"""
from django.contrib.sessions.middleware import SessionMiddleware
from django.test.client import RequestFactory

from affiliate.constants import AFFILIATE_QS_PARAM
from affiliate.middleware import AffiliateMiddleware


def test_affiliate_middleware(mocker):
    """
    AffiliateMiddleware should add the affiliate code to the session if a code was passed in the querystring,
    and add an attribute to the request object
    """
    affiliate_code = "abc"
    request = RequestFactory().get(f"/?{AFFILIATE_QS_PARAM}={affiliate_code}")

    # Add session capability to the request
    SessionMiddleware().process_request(request)
    request.session.save()

    middleware = AffiliateMiddleware(get_response=mocker.Mock())
    middleware(request)
    assert request.affiliate_code == affiliate_code
    assert request.session["affiliate_code"] == affiliate_code


def test_affiliate_middleware_session(mocker):
    """AffiliateMiddleware should add add an attribute to the request object if a code exists in the session"""
    affiliate_code = "abc"
    request = RequestFactory().get("/")

    # Add session capability to the request and add the affiliate code to the session
    SessionMiddleware().process_request(request)
    request.session["affiliate_code"] = affiliate_code
    request.session.save()

    middleware = AffiliateMiddleware(get_response=mocker.Mock())
    middleware(request)
    assert request.affiliate_code == affiliate_code

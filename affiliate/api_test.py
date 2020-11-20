"""Affiliate tracking logic"""
import pytest
from django.test.client import RequestFactory

from affiliate.api import (
    get_affiliate_code_from_qstring,
    get_affiliate_code_from_request,
    get_affiliate_id_from_code,
    get_affiliate_id_from_request,
)
from affiliate.constants import AFFILIATE_QS_PARAM
from affiliate.factories import AffiliateFactory


def test_get_affiliate_code_from_qstring():
    """
    get_affiliate_code_from_qstring should get the affiliate code from the querystring
    """
    affiliate_code = "abc"
    request = RequestFactory().post(f"/?{AFFILIATE_QS_PARAM}={affiliate_code}", data={})
    code = get_affiliate_code_from_qstring(request)
    assert code is None
    request = RequestFactory().get("/")
    code = get_affiliate_code_from_qstring(request)
    assert code is None
    request = RequestFactory().get(f"/?{AFFILIATE_QS_PARAM}={affiliate_code}")
    code = get_affiliate_code_from_qstring(request)
    assert code == affiliate_code


def test_get_affiliate_code_from_request():
    """
    get_affiliate_code_from_request should get the affiliate code from a request object
    """
    affiliate_code = "abc"
    request = RequestFactory().get("/")
    code = get_affiliate_code_from_request(request)
    assert code is None
    setattr(request, "affiliate_code", affiliate_code)
    code = get_affiliate_code_from_request(request)
    assert code == affiliate_code


@pytest.mark.django_db
def test_get_affiliate_id_from_code():
    """
    get_affiliate_id_from_code should fetch the Affiliate id from the database that matches the affiliate code
    """
    affiliate_code = "abc"
    affiliate_id = get_affiliate_id_from_code(affiliate_code)
    assert affiliate_id is None
    affiliate = AffiliateFactory.create(code=affiliate_code)
    affiliate_id = get_affiliate_id_from_code(affiliate_code)
    assert affiliate_id == affiliate.id


@pytest.mark.django_db
def test_get_affiliate_id_from_request():
    """
    get_affiliate_id_from_request should fetch the Affiliate id from the database that matches the
    affiliate code from the request
    """
    affiliate_code = "abc"
    request = RequestFactory().get("/")
    setattr(request, "affiliate_code", affiliate_code)
    affiliate_id = get_affiliate_id_from_request(request)
    assert affiliate_id is None
    affiliate = AffiliateFactory.create(code=affiliate_code)
    affiliate_id = get_affiliate_id_from_request(request)
    assert affiliate_id == affiliate.id

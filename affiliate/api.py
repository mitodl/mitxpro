"""Affiliate tracking logic"""
from affiliate.constants import AFFILIATE_QS_PARAM
from affiliate.models import Affiliate
from mitxpro.utils import first_or_none


def get_affiliate_code_from_qstring(request):
    """
    Gets the affiliate code from the querystring if one exists

    Args:
        request (django.http.request.HttpRequest): A request

    Returns:
        Optional[str]: The affiliate code (or None)
    """
    if request.method != "GET":
        return None
    affiliate_code = request.GET.get(AFFILIATE_QS_PARAM)
    return affiliate_code


def get_affiliate_code_from_request(request):
    """
    Helper method that gets the affiliate code from a request object if it exists

    Args:
        request (django.http.request.HttpRequest): A request

    Returns:
        Optional[str]: The affiliate code (or None)
    """
    return getattr(request, "affiliate_code", None)


def get_affiliate_id_from_code(affiliate_code):
    """
    Helper method that fetches the Affiliate id from the database that matches the affiliate code

    Args:
        affiliate_code (str): The affiliate code

    Returns:
        Optional[Affiliate]: The id of the Affiliate that matches the given code (if it exists)
    """
    return first_or_none(
        Affiliate.objects.filter(code=affiliate_code).values_list("id", flat=True)
    )


def get_affiliate_id_from_request(request):
    """
    Helper method that fetches the Affiliate id from the database that matches the affiliate code from the request

    Args:
        request (django.http.request.HttpRequest): A request

    Returns:
        Optional[Affiliate]: The Affiliate object that matches the affiliate code in the request (or None)
    """
    affiliate_code = get_affiliate_code_from_request(request)
    return (
        get_affiliate_id_from_code(affiliate_code)
        if affiliate_code is not None
        else None
    )

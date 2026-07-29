"""
Exceptions for ecommerce
"""


class EcommerceException(Exception):  # noqa: N818
    """
    General exception regarding ecommerce
    """


class EcommerceEdxApiException(Exception):  # noqa: N818
    """
    Exception regarding edx_api_client
    """


class EcommerceModelException(Exception):  # noqa: N818
    """
    Exception regarding ecommerce models
    """


class ParseException(Exception):  # noqa: N818
    """
    Exception regarding parsing CyberSource reference numbers
    """

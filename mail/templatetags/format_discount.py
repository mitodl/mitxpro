"""Custom template tags for email"""
from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def format_discount(discount_amount):
    """
    Formats the discount amount to be displayed in $

    Args:
        discount_amount (Decimal): Discount amount

    Returns:
        str: Formatted discount amount, Would return "$0" and "-${discount}" for all others
    """  # noqa: D401
    discount_amount = abs(Decimal(discount_amount))
    return f"{'' if discount_amount == 0 else '-'}${abs(discount_amount.quantize(Decimal('.01')))}"

"""Calculate tax charged for an item"""
from django import template

from mail.templatetags.calculate_tax import calculate_tax


register = template.Library()


@register.filter
def calculate_tax_total(total_paid, tax_rate):
    """
    Calculates the tax amount for an item and returns a sum of those

    Args:
        total_paid (Decimal): Total paid
        tax_rate (Decimal): Tax rate to assess as a whole number (18 rather than 0.18)

    Returns:
        datetime: the parsed datetime
    """
    return calculate_tax(total_paid, tax_rate) + total_paid

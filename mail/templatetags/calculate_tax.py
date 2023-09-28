"""Calculate tax charged for an item"""
from decimal import Decimal

from django import template


register = template.Library()


@register.filter
def calculate_tax(total_paid, tax_rate):
    """
    Calculates the tax amount for an item

    Args:
        total_paid (Decimal): Total paid
        tax_rate (Decimal): Tax rate to assess as a whole number (18 rather than 0.18)

    Returns:
        Decimal: the tax assessed, quantized to .01
    """
    return Decimal(total_paid * (tax_rate / 100)).quantize(Decimal(".01"))

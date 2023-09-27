"""Calculate tax charged for an item"""
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
        datetime: the parsed datetime
    """
    return total_paid * (tax_rate / 100)

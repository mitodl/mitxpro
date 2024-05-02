"""Custom template tags for email"""

from dateutil.parser import parse
from django import template

register = template.Library()


@register.filter
def parse_iso(value):
    """
    Parses an iso datetime string into a datetime object

    Args:
        value (str): datetime str

    Returns:
        datetime: the parsed datetime
    """
    return parse(value)

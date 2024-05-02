"""Module for custom string utility template tags and filters"""

from django import template

register = template.Library()


@register.filter("startswith")
def startswith(text, starts):
    """Filter to check if a string starts with a specific format"""
    if isinstance(text, str):
        starts = starts.split(",")
        for start in starts:
            if text.startswith(start):
                return True
    return False

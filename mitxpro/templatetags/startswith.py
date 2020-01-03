"""Module for custom string utility template tags and filters"""
from django import template

register = template.Library()


@register.filter("startswith")
def startswith(text, starts):
    """Filter to check if a string starts with a specific format"""
    if isinstance(text, str):
        return text.startswith(starts)
    return False

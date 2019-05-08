from django import template

register = template.Library()


@register.filter
def make_fragment_id(value):
    """
    Takes value and make it lowercase and join with '-', which can be used as fragment identifier.
    """
    value = value.lower()
    return value.replace(" ", "-")

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def dateful_url(datetime_obj):
    """
    Convert a DateTimeField object to a dateful.com URL for timezone conversion

    Args:
        datetime_obj (datetime): The DateTimeField object to convert.

    Returns:
        str: The dateful.com URL for the given datetime object.
    """
    if not datetime_obj:
        return ""

    if timezone.is_naive(datetime_obj):
        datetime_obj = timezone.make_aware(datetime_obj, timezone.utc)

    time_param = datetime_obj.strftime("%H%M")
    date_param = datetime_obj.strftime("%Y-%m-%d")

    return f"https://dateful.com/convert/utc?t={time_param}&d={date_param}"

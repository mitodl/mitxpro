"""CMS templatetags"""

from urllib.parse import quote_plus
from django import template
from wagtail.images.templatetags.wagtailimages_tags import image_url

register = template.Library()


@register.simple_tag()
def image_version_url(image, filter_spec, viewname="wagtailimages_serve"):
    """Generates an image URL using Wagtails library and appends a version to the path to enable effective caching"""
    generated_image_url = image_url(image, filter_spec, viewname=viewname)
    return (
        f"{generated_image_url}?v={quote_plus(image.file_hash)}"
        if generated_image_url
        else ""
    )

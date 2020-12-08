"""CMS templatetags"""

from urllib.parse import quote_plus, urljoin
from django import template
from django.conf import settings
from wagtail.images.templatetags.wagtailimages_tags import image_url

register = template.Library()


@register.simple_tag()
def image_version_url(
    image, filter_spec, full_url=False, viewname="wagtailimages_serve"
):
    """
    Generates an image URL using Wagtail's library and appends a version to the path to enable effective caching

    Args:
        image (wagtail.images.models.Image): The image the a URL will be generated for
        filter_spec (str): A filter specification for the image (see Wagtail docs)
        full_url (bool): If True, generates the image URL with the full base URL instead of just a relative URL
        viewname (str): The view name to use for generating the URL

    Returns:
        str or None: The image URL, or None if the image doesn't exist
    """
    if not image:
        return ""
    generated_image_url = image_url(image, filter_spec, viewname=viewname)
    if not generated_image_url:
        return ""
    if full_url:
        generated_image_url = urljoin(settings.SITE_BASE_URL, generated_image_url)
    return f"{generated_image_url}?v={quote_plus(image.file_hash)}"

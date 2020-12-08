"""Tests for custom CMS templatetags"""
from urllib.parse import urljoin

import pytest
from wagtail.images.views.serve import generate_signature
from wagtail_factories import ImageFactory

from cms.templatetags.image_version_url import image_version_url

BASE_URL = "http://localhost"


@pytest.mark.parametrize("full_url", [True, False])
def test_image_version_url(settings, full_url):
    """image_version_url should produce an image URL with the file hash set as the file version in the querystring"""
    settings.SITE_BASE_URL = BASE_URL
    view_name = "wagtailimages_serve"
    image_id = 1
    file_hash = "abcdefg"
    image_filter = "fill-75x75"
    image = ImageFactory.build(id=image_id, file_hash=file_hash)
    expected_signature = generate_signature(image_id, image_filter, key=None)
    result_url = image_version_url(
        image, image_filter, full_url=full_url, viewname=view_name
    )
    relative_url = (
        f"/images/{expected_signature}/{image_id}/{image_filter}/?v={file_hash}"
    )
    expected_result_url = (
        relative_url if full_url is False else urljoin(BASE_URL, relative_url)
    )
    assert result_url == expected_result_url

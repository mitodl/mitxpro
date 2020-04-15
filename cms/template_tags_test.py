"""Tests for custom CMS templatetags"""
import pytest
from wagtail.images.views.serve import generate_signature
from wagtail_factories import ImageFactory

from cms.templatetags.image_version_url import image_version_url


@pytest.mark.django_db
def test_image_version_url():
    """image_version_url should produce an image URL with the file hash set as the file version in the querystring"""
    view_name = "wagtailimages_serve"
    image_id = 1
    file_hash = "abcdefg"
    image_filter = "fill-75x75"
    image = ImageFactory.build(id=image_id, file_hash=file_hash)
    expected_signature = generate_signature(image_id, image_filter, key=None)
    result_url = image_version_url(image, image_filter, viewname=view_name)
    assert (
        result_url
        == f"/images/{expected_signature}/{image_id}/{image_filter}/?v={file_hash}"
    )

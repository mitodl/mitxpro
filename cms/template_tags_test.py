"""Tests for custom CMS templatetags"""
from re import findall
from urllib.parse import urljoin

from django.template import Context, Template
import pytest

from wagtail.images.views.serve import generate_signature
from wagtail.images.tests.utils import get_test_image_file_jpeg
from wagtail.images.models import Image
from wagtail_factories import ImageFactory

from cms.templatetags.image_version_url import image_version_url

BASE_URL = "http://localhost"
pytestmark = [pytest.mark.django_db]


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


def test_wagtail_lazy_image():
    """
    wagtail_lazy_image should produce an image template tag having url of placeholder image in src and
    url of original image in data-src along with the file hash set as the file version in the querystring
    """
    file_hash = "abcdefg"
    image_filter = "fill-75x75"
    image_file = get_test_image_file_jpeg(size=(1280, 720))
    image = Image.objects.create(title="Test", file=image_file, file_hash=file_hash)

    custom_template = Template(
        "{% load wagtail_lazy_image %}"
        "{% wagtail_lazy_image image " + image_filter + " %}"
    )
    plugin_template = Template(
        "{% load lazyimages_tags %}" "{% lazy_image image " + image_filter + " %}"
    )

    actuall_img_tag = custom_template.render(Context({"image": image}))
    expected_img_tag = plugin_template.render(Context({"image": image}))

    for link in findall(r"src=(.+?)\s", expected_img_tag):
        expected_img_tag = expected_img_tag.replace(
            link, f"{link[:-1]}?v={file_hash}{link[-1]}"
        )

    assert actuall_img_tag == expected_img_tag

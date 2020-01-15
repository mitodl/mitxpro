"""Tests for custom embed providers and finders"""
import pytest
from django.core.exceptions import ImproperlyConfigured
from wagtail.embeds.oembed_providers import vimeo

from cms.embeds import YouTubeEmbedFinder

pytestmark = pytest.mark.django_db


def test_youtube_finder_invalid_config():
    """
    Test that the Youtube embed finder throws in invalid configuration exception
    if used apart from the Youtube provider
    """
    with pytest.raises(ImproperlyConfigured):
        assert YouTubeEmbedFinder(providers=[vimeo])

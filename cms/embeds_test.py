"""Tests for custom embed providers and finders"""
from urllib.parse import parse_qs, urlparse

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ImproperlyConfigured
from wagtail.embeds.embeds import get_embed
from wagtail.embeds.exceptions import EmbedNotFoundException
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


def test_youtube_embed():
    """
    Test that the Youtube embed works with a Youtube link.
    """
    embed = get_embed("https://www.youtube.com/watch?v=C0DPdy98e4c")
    assert embed
    assert embed.html


def test_youtube_embed_parameters():
    """
    Test that the Youtube embed works with a Youtube link.
    """
    embed = get_embed("https://www.youtube.com/watch?v=C0DPdy98e4c")
    assert embed
    assert embed.html

    embed_tag = BeautifulSoup(embed.html, "html.parser")
    iframe_url = embed_tag.find("iframe").attrs["src"]
    _, _, _, _, query, _ = urlparse(iframe_url)

    querydict = parse_qs(query)
    assert querydict["rel"] == ["0"]
    assert querydict["enablejsapi"] == ["1"]


def test_youtube_embed_invalid_link():
    """
    Test that the Youtube embed throws an exception on an invalid link
    """
    with pytest.raises(EmbedNotFoundException):
        assert get_embed("https://www.youtube.com/watch?v=DUMMY")

"""
Custom wagtail embed providers and finders
"""

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.core.exceptions import ImproperlyConfigured

from bs4 import BeautifulSoup
from wagtail.embeds.finders.oembed import OEmbedFinder
from wagtail.embeds.oembed_providers import youtube


class YouTubeEmbedFinder(OEmbedFinder):
    """
    OEmbed finder which injects rel=0 and enablejsapi=1 parameters on YouTube URLs.

    This finder operates on the youtube provider only, and sets the
    source URL's rel=0  and enablejsapi=1. By default Youtube strips these out.
    """

    def __init__(self, providers=None, options=None):
        if providers is None:
            providers = [youtube]

        if providers != [youtube]:
            raise ImproperlyConfigured(
                "The YouTubeEmbedFinder only operates on the youtube provider"
            )

        super().__init__(providers=providers, options=options)

    def find_embed(self, url, max_width=None):
        embed = super().find_embed(url, max_width)
        embed_tag = BeautifulSoup(embed["html"], "html.parser")
        player_iframe = embed_tag.find("iframe")
        iframe_url = player_iframe.attrs["src"]
        scheme, netloc, path, params, query, fragment = urlparse(iframe_url)

        querydict = parse_qs(query)
        querydict["rel"] = "0"
        querydict["enablejsapi"] = "1"

        query = urlencode(querydict, doseq=1)
        iframe_url = urlunparse((scheme, netloc, path, params, query, fragment))
        player_iframe.attrs["loading"] = "lazy"
        player_iframe.attrs["src"] = ""
        player_iframe.attrs["data-src"] = iframe_url
        embed["html"] = str(embed_tag)

        return embed

"""
Views for the Blog app
"""
import requests

import xmltodict
from django.core.cache import cache
from django.views import View
from django.shortcuts import render

from blog.api import transform_blog_item


class BlogView(View):
    """View for blogs"""

    template_name = "blog.html"
    CACHE_KEY = "blog-items"
    CACHE_TIMEOUT = 24 * 60 * 60

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Fetch blog xml.
        """
        items = cache.get(self.CACHE_KEY)
        if items:
            return render(request, self.template_name, {"posts": items})

        rss_feed_url = "https://curve.mit.edu/rss.xml"
        resp = requests.get(rss_feed_url, timeout=60)
        resp.raise_for_status()
        resp_dict = xmltodict.parse(resp.content)

        items = resp_dict.get("rss", {}).get("channel", {}).get("item", [])
        for item in items:
            transform_blog_item(item)
        cache.set(self.CACHE_KEY, items, self.CACHE_TIMEOUT)
        return render(request, self.template_name, {"posts": items})

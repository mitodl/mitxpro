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

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Fetch blog xml.
        """
        items = cache.get("blog-items")
        if items:
            return render(request, self.template_name, {"posts": items})

        rss_feed_url = "https://curve.mit.edu/rss.xml"
        resp = requests.get(rss_feed_url, timeout=60)
        resp.raise_for_status()
        resp_dict = xmltodict.parse(resp.content)

        items = resp_dict.get("rss", {}).get("channel", {}).get("item", [])
        for item in items:
            transform_blog_item(item)
        cache.set("blog-items", items, 24 * 60 * 60)
        return render(request, self.template_name, {"posts": items})

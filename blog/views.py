"""
Views for the Blog app
"""
from django.core.cache import cache
from django.shortcuts import render
from django.views import View

from blog.api import fetch_blogs


class BlogView(View):
    """View for blogs"""

    template_name = "blog.html"
    CACHE_KEY = "blog-items"
    CACHE_TIMEOUT = 24 * 60 * 60  # 24 hours

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Fetch blogs
        """
        items = cache.get(self.CACHE_KEY)
        if items:
            return render(request, self.template_name, {"posts": items})

        items = fetch_blogs()
        cache.set(self.CACHE_KEY, items, self.CACHE_TIMEOUT)
        return render(request, self.template_name, {"posts": items})

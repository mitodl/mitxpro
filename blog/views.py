"""
Views for the Blog app
"""
import requests
import xmltodict
from rest_framework.response import Response
from rest_framework.views import APIView

from blog.api import transform_blog_item


class BlogListView(APIView):
    """Fetch blogs and convert to a JSON format"""

    permission_classes = []

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        rss_feed_url = "https://curve.mit.edu/rss.xml"

        resp = requests.get(rss_feed_url, timeout=60)
        resp.raise_for_status()
        resp_dict = xmltodict.parse(resp.content)
        items = resp_dict.get("rss", {}).get("channel", {}).get("item", [])
        for item in items:
            transform_blog_item(item)
        return Response({"posts": items})

"""Tests for URLs"""

from unittest import TestCase
from django.urls import reverse


class URLTests(TestCase):
    """URL tests"""

    def test_urls(self):
        """Make sure URLs match with resolved names"""
        assert reverse("mitxpro-index") == "/"

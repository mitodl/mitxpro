"""Tests for CMS views"""
import pytest

from django.urls import reverse
from wagtail.core.models import Site

from cms.models import HomePage

pytestmark = pytest.mark.django_db


def test_home_page_view(client):
    """
    Test that the home page shows the right HTML for the watch now button
    """
    root = Site.objects.get(is_default_site=True).root_page
    page = HomePage(title="Home Page", subhead="<p>subhead</p>")
    root.add_child(instance=page)
    resp = client.get(page.get_url())
    content = resp.content.decode("utf-8")

    assert (
        f'<a id="actionButton" class="enroll-button" href="#">Watch Now</a>' in content
    )
    assert reverse("user-dashboard") not in content
    assert reverse("checkout-page") not in content
    assert "dropdown-menu" not in content

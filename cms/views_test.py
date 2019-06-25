"""Tests for CMS views"""
import pytest

from django.urls import reverse
from wagtail.core.models import Site
from rest_framework import status

from cms.factories import TextSectionFactory
from cms.models import HomePage, CourseIndexPage, ProgramIndexPage

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
        f'<a id="actionButton" class="btn btn-primary text-uppercase px-5 py-2 action-button" href="#">Watch Now</a>'
        in content
    )
    assert reverse("user-dashboard") not in content
    assert reverse("checkout-page") not in content
    assert "dropdown-menu" not in content


def test_courses_index_view(client):
    """
    Test that the courses index page shows a 404
    """
    root = Site.objects.get(is_default_site=True).root_page
    page, created = CourseIndexPage.objects.get_or_create()

    if created:
        root.add_child(instance=page)

    resp = client.get(page.get_url())
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_programs_index_view(client):
    """
    Test that the programs index page shows a 404
    """
    root = Site.objects.get(is_default_site=True).root_page
    page, created = ProgramIndexPage.objects.get_or_create()

    if created:
        root.add_child(instance=page)

    resp = client.get(page.get_url())
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_course_program_child_view(client):
    """
    Test that course/program child pages show a 404
    """
    root = Site.objects.get(is_default_site=True).root_page

    child_page = TextSectionFactory.create(parent=root)
    child_page.save_revision().publish()
    resp = client.get(child_page.get_url())
    assert resp.status_code == status.HTTP_404_NOT_FOUND

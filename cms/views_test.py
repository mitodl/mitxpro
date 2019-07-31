"""Tests for CMS views"""
from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from wagtail.core.models import Site

from cms.factories import (
    CatalogPageFactory,
    CoursePageFactory,
    ProgramPageFactory,
    TextSectionFactory,
)
from cms.models import CourseIndexPage, HomePage, ProgramIndexPage
from courses.factories import CourseFactory, CourseRunFactory
from mitxpro.utils import now_in_utc

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


def test_catalog_page_product(client):
    """
    Verify that the catalog page does not include cards for either product pages
    that are not live (unpublished) or pages that have a product with live=False
    """
    homepage = Site.objects.get(is_default_site=True).root_page

    catalog_page = CatalogPageFactory.create(parent=homepage)
    catalog_page.save_revision().publish()

    now = now_in_utc()
    start_date = now + timedelta(days=2)
    end_date = now + timedelta(days=10)

    # Live course page and course with a future course run. Should be included in upcoming context
    active_course_page = CoursePageFactory.create(course__live=True)
    CourseRunFactory.create(
        course=active_course_page.product,
        start_date=start_date,
        end_date=end_date,
        live=True,
    )

    # Live program page and program containing a live course with a future course run. Should be
    # included in upcoming context
    active_program_page = ProgramPageFactory.create(program__live=True)
    active_program_course = CourseFactory.create(
        program=active_program_page.product, live=True
    )
    CourseRunFactory.create(
        course=active_program_course,
        start_date=start_date,
        end_date=end_date,
        live=True,
    )

    # The course isn't live however it has a valid and live run. This should be filtered out in the
    # upcoming template context
    inactive_course_page = CoursePageFactory.create(course__live=False)
    CourseRunFactory.create(
        course=inactive_course_page.product,
        start_date=start_date,
        end_date=end_date,
        live=True,
    )

    # Both the course and course run are live, however the program is not. This should be filtered
    # out in the upcoming template context
    inactive_program_page = ProgramPageFactory.create(program__live=False)
    inactive_program_course = CourseFactory.create(
        program=inactive_program_page.product, live=True
    )
    CourseRunFactory.create(
        course=inactive_program_course,
        start_date=start_date,
        end_date=end_date,
        live=True,
    )

    resp = client.get(catalog_page.get_url())
    assert resp.status_code == status.HTTP_200_OK
    assert resp.context_data["course_pages"] == [active_course_page]
    assert resp.context_data["program_pages"] == [active_program_page]

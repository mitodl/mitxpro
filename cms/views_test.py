"""Tests for CMS views"""
from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework import status
from wagtail.core.models import Site, Page

from cms.factories import (
    CatalogPageFactory,
    CoursePageFactory,
    ProgramPageFactory,
    TextSectionFactory,
    CertificatePageFactory,
    HomePageFactory,
)
from cms.models import CourseIndexPage, HomePage, ProgramIndexPage, TextVideoSection
from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    CourseRunCertificateFactory,
    ProgramCertificateFactory,
)

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

    # without watch now button
    assert (
        f'<a id="actionButton" class="btn btn-primary text-uppercase px-5 py-2 action-button" href="#">Watch Now</a>'
        not in content
    )
    assert "dropdown-menu" in content

    # add video section
    about_page = TextVideoSection(
        content="<p>content</p>", video_url="http://test.com/abcd"
    )
    page.add_child(instance=about_page)
    resp = client.get(page.get_url())
    content = resp.content.decode("utf-8")

    # with watch now button
    assert (
        f'<a id="actionButton" class="btn btn-primary text-uppercase px-5 py-2 action-button" href="#">Watch Now</a>'
        in content
    )
    assert "dropdown-menu" not in content

    assert reverse("user-dashboard") not in content
    assert reverse("checkout-page") not in content


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


def test_course_certificate_invalid_view(user_client, user):
    """
    Test that certificate page returns a 404 if CertificatePage does not exist for that course
    """
    site = Site.objects.get(is_default_site=True)
    root = Page.objects.get(depth=1)

    old_home = Page.objects.filter(depth=2).first()
    old_home.slug = "some-slug"
    old_home.save_revision().publish()

    home = HomePageFactory.create(parent=root, slug="home")
    home.save_revision().publish()
    site.root_page = home
    site.save()

    subpages = old_home.get_children()

    for subpage in subpages:
        subpage.move(home, "last-child")

    course_page = CoursePageFactory.create(parent=home)
    course_page.save_revision().publish()

    course_run_certificate = CourseRunCertificateFactory.create(
        user=user, course_run__course=course_page.course
    )

    resp = user_client.get(course_run_certificate.link)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_course_certificate_view(user_client, user):
    """
    Test that certificate page show correctly
    """
    site = Site.objects.get(is_default_site=True)
    root = Page.objects.get(depth=1)

    old_home = Page.objects.filter(depth=2).first()
    old_home.slug = "some-slug"
    old_home.save_revision().publish()

    home = HomePageFactory.create(parent=root, slug="home")
    home.save_revision().publish()
    site.root_page = home
    site.save()

    subpages = old_home.get_children()

    for subpage in subpages:
        subpage.move(home, "last-child")

    course_page = CoursePageFactory.create(parent=home)
    course_page.save_revision().publish()

    certificate_page = CertificatePageFactory.create(parent=course_page)
    certificate_page.save_revision().publish()

    course_run = CourseRunFactory.create(course=course_page.course)

    course_run_certificate = CourseRunCertificateFactory.create(
        user=user, course_run=course_run
    )

    resp = user_client.get(course_run_certificate.link)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.context_data["page"] == certificate_page
    assert resp.context_data["page"].certificate == course_run_certificate


def test_course_certificate_view_revoked_state(user_client, user):
    """
    Test that certificate page return 404 for revoked certificate.
    """
    site = Site.objects.get(is_default_site=True)
    root = Page.objects.get(depth=1)

    old_home = Page.objects.filter(depth=2).first()
    old_home.slug = "some-slug"
    old_home.save_revision().publish()

    home = HomePageFactory.create(parent=root, slug="home")
    home.save_revision().publish()
    site.root_page = home
    site.save()

    subpages = old_home.get_children()

    for subpage in subpages:
        subpage.move(home, "last-child")

    course_page = CoursePageFactory.create(parent=home)
    course_page.save_revision().publish()

    certificate_page = CertificatePageFactory.create(parent=course_page)
    certificate_page.save_revision().publish()

    course_run = CourseRunFactory.create(course=course_page.course)

    course_run_certificate = CourseRunCertificateFactory.create(
        user=user, course_run=course_run, is_revoked=False
    )

    resp = user_client.get(course_run_certificate.link)
    assert resp.status_code == status.HTTP_200_OK

    course_run_certificate.is_revoked = True
    course_run_certificate.save()
    resp = user_client.get(course_run_certificate.link)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_program_certificate_invalid_view(user_client, user):
    """
    Test that program certificate page returns a 404 if CertificatePage does not exist for that program
    """
    site = Site.objects.get(is_default_site=True)
    root = Page.objects.get(depth=1)

    old_home = Page.objects.filter(depth=2).first()
    old_home.slug = "some-slug"
    old_home.save_revision().publish()

    home = HomePageFactory.create(parent=root, slug="home")
    home.save_revision().publish()
    site.root_page = home
    site.save()

    subpages = old_home.get_children()

    for subpage in subpages:
        subpage.move(home, "last-child")

    program_page = ProgramPageFactory.create(parent=home)
    program_page.save_revision().publish()

    program_certificate = ProgramCertificateFactory.create(
        user=user, program=program_page.program
    )

    resp = user_client.get(program_certificate.link)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_program_certificate_view(user_client, user):
    """
    Test that certificate page show correctly
    """
    site = Site.objects.get(is_default_site=True)
    root = Page.objects.get(depth=1)

    old_home = Page.objects.filter(depth=2).first()
    old_home.slug = "some-slug"
    old_home.save_revision().publish()

    home = HomePageFactory.create(parent=root, slug="home")
    home.save_revision().publish()
    site.root_page = home
    site.save()

    subpages = old_home.get_children()

    for subpage in subpages:
        subpage.move(home, "last-child")

    program_page = ProgramPageFactory.create(parent=home)
    program_page.save_revision().publish()

    certificate_page = CertificatePageFactory.create(parent=program_page)
    certificate_page.save_revision().publish()

    program_certificate = ProgramCertificateFactory.create(
        user=user, program=program_page.program
    )

    resp = user_client.get(program_certificate.link)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.context_data["page"] == certificate_page
    assert resp.context_data["page"].certificate == program_certificate


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

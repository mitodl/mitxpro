""" Tests for cms pages. """

import json
import pytest

from cms.factories import (
    ResourcePageFactory,
    SiteNotificationFactory,
    ForTeamsPageFactory,
    UserTestimonialsPageFactory,
    CoursesInProgramPageFactory,
    HomePageFactory,
    ProgramPageFactory,
    CoursePageFactory,
)

from courses.factories import CourseFactory

pytestmark = [pytest.mark.django_db]


def test_resource_page():
    """
    Verify user can create resource page.
    """
    page = ResourcePageFactory.create(
        title="title of the page",
        sub_heading="sub heading of the page",
        content=json.dumps(
            [
                {
                    "type": "content",
                    "value": {
                        "heading": "Introduction",
                        "detail": "details of introduction",
                    },
                }
            ]
        ),
    )

    assert page.title == "title of the page"
    assert page.sub_heading == "sub heading of the page"

    for block in page.content:  # pylint: disable=not-an-iterable
        assert block.block_type == "content"
        assert block.value["heading"] == "Introduction"
        assert block.value["detail"].source == "details of introduction"


def test_notification_snippet():
    """
    Verify that user can create site notification using cms.
    """
    message_text = "<p>hello this is a test notification</p>"
    notification = SiteNotificationFactory(message=message_text)

    assert str(notification) == message_text


def test_course_page_program_page():
    """
    Verify `program_page` property from the course page returns expected value
    """
    program_page = ProgramPageFactory.create()
    course_page = CoursePageFactory.create(course__program=program_page.program)
    assert course_page.program_page == program_page


def test_program_page_course_pages():
    """
    Verify `course_pages` property from the program page returns expected value
    """
    program_page = ProgramPageFactory.create()
    assert list(program_page.course_pages) == []
    course_page = CoursePageFactory.create(course__program=program_page.program)
    assert list(program_page.course_pages) == [course_page]


def test_home_page():
    """
    Verify that home page is created
    """
    page = HomePageFactory.create(title="Home Page", subhead="<p>subhead</p>")
    assert page.title == "Home Page"
    assert page.subhead == "<p>subhead</p>"


def test_home_page_testimonials():
    """
    Testimonials subpage should provide expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.testimonials
    testimonials_page = UserTestimonialsPageFactory.create(
        parent=home_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__title="image",
        items__0__testimonial__quote="quote",
        items__1__testimonial__name="name",
        items__1__testimonial__title="title",
        items__1__testimonial__image__title="image",
        items__1__testimonial__quote="quote",
    )
    assert home_page.testimonials == testimonials_page
    assert testimonials_page.heading == "heading"
    assert testimonials_page.subhead == "subhead"
    for testimonial in testimonials_page.items:  # pylint: disable=not-an-iterable
        assert testimonial.value.get("name") == "name"
        assert testimonial.value.get("title") == "title"
        assert testimonial.value.get("image").title == "image"
        assert testimonial.value.get("quote") == "quote"


def test_home_page_inquiry_section():
    """
    inquiry_section property should return expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.inquiry_section
    inquiry_page = ForTeamsPageFactory.create(
        parent=home_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
    )
    assert home_page.inquiry_section == inquiry_page
    assert inquiry_page.action_title == "Action Title"
    assert inquiry_page.content == "<p>content</p>"
    assert inquiry_page.switch_layout
    assert inquiry_page.dark_theme


def test_home_page_upcoming_courseware():
    """
    upcoming_courseware property should return expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.upcoming_courseware
    course = CourseFactory.create()
    carousel_page = CoursesInProgramPageFactory.create(
        parent=home_page,
        heading="heading",
        body="<p>body</p>",
        override_contents=True,
        contents__0__item__course=course,
    )
    assert home_page.upcoming_courseware == carousel_page
    assert carousel_page.heading == "heading"
    assert carousel_page.body == "<p>body</p>"
    assert carousel_page.override_contents
    assert carousel_page.content_pages == [course.page]

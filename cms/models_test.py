""" Tests for cms pages. """

import json
import pytest
import factory

from django.urls import resolve

from cms.factories import (
    ResourcePageFactory,
    SiteNotificationFactory,
    ForTeamsPageFactory,
    UserTestimonialsPageFactory,
    CoursesInProgramPageFactory,
    HomePageFactory,
    ProgramPageFactory,
    CoursePageFactory,
    TextVideoSectionFactory,
    ImageCarouselPageFactory,
    FacultyMembersPageFactory,
    LearningTechniquesPageFactory,
    FrequentlyAskedQuestionPageFactory,
    FrequentlyAskedQuestionFactory,
    LearningOutcomesPageFactory,
    WhoShouldEnrollPageFactory,
    TextSectionFactory,
)
from cms.models import (
    UserTestimonialsPage,
    ForTeamsPage,
    CoursesInProgramPage,
    FrequentlyAskedQuestionPage,
    LearningOutcomesPage,
    LearningTechniquesPage,
    WhoShouldEnrollPage,
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


def test_custom_detail_page_urls():
    """Verify that course/program detail pages return our custom URL path"""
    readable_id = "some:readable-id"
    program_pages = ProgramPageFactory.create_batch(
        2, program__readable_id=factory.Iterator([readable_id, "non-matching-id"])
    )
    course_pages = CoursePageFactory.create_batch(
        2, course__readable_id=factory.Iterator([readable_id, "non-matching-id"])
    )
    assert program_pages[0].get_url() == "/programs/{}/".format(readable_id)
    assert course_pages[0].get_url() == "/courses/{}/".format(readable_id)


def test_custom_detail_page_urls_handled():
    """Verify that custom URL paths for our course/program are served by the standard Wagtail view"""
    readable_id = "some:readable-id"
    CoursePageFactory.create(course__readable_id=readable_id)
    resolver_match = resolve("/courses/{}/".format(readable_id))
    assert (
        resolver_match.func.__module__ == "wagtail.core.views"
    )  # pylint: disable=protected-access
    assert resolver_match.func.__name__ == "serve"  # pylint: disable=protected-access


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


def test_home_page_about_mit_xpro():
    """
    about_mit_xpro property should return expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.about_mit_xpro
    about_page = TextVideoSectionFactory.create(
        parent=home_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
        video_url="http://test.com/abcd",
    )
    assert home_page.about_mit_xpro == about_page
    assert about_page.action_title == "Action Title"
    assert about_page.content == "<p>content</p>"
    assert about_page.video_url == "http://test.com/abcd"
    assert about_page.switch_layout
    assert about_page.dark_theme


def test_image_carousel_section():
    """
    image_carousel_section property should return expected values.
    """
    home_page = HomePageFactory.create()
    assert not home_page.image_carousel_section
    image_carousel_page = ImageCarouselPageFactory.create(
        parent=home_page,
        title="title",
        images__0__image__image__title="image-title-0",
        images__1__image__image__title="image-title-1",
        images__2__image__image__title="image-title-2",
        images__3__image__image__title="image-title-3",
    )
    assert home_page.image_carousel_section == image_carousel_page
    assert image_carousel_page.title == "title"
    for index, image in enumerate(image_carousel_page.images):
        assert image.value.title == "image-title-{}".format(index)


def test_program_page_faculty_subpage():
    """
    FacultyMembersPage should return expected values if associated with ProgramPage
    """
    program_page = ProgramPageFactory.create()

    assert not program_page.faculty
    FacultyMembersPageFactory.create(
        parent=program_page, members=json.dumps(_get_faculty_members())
    )
    _assert_faculty_members(program_page)


def test_course_page_faculty_subpage():
    """
    FacultyMembersPage should return expected values if associated with CoursePage
    """
    course_page = CoursePageFactory.create()

    assert not course_page.faculty
    FacultyMembersPageFactory.create(
        parent=course_page, members=json.dumps(_get_faculty_members())
    )
    _assert_faculty_members(course_page)


def _get_faculty_members():
    """Provides a `faculty` property instantiation data"""
    return [
        {
            "type": "member",
            "value": {"name": "Test Faculty", "description": "<p>description</p>"},
        },
        {
            "type": "member",
            "value": {"name": "Test Faculty", "description": "<p>description</p>"},
        },
    ]


def _assert_faculty_members(obj):
    """Verifies `faculty` property returns expected value"""
    assert obj.faculty
    for block in obj.faculty.members:
        assert block.block_type == "member"
        assert block.value["name"] == "Test Faculty"
        assert block.value["description"].source == "<p>description</p>"


def test_course_page_testimonials():
    """
    testimonials property should return expected value if associated with a CoursePage
    """
    course_page = CoursePageFactory.create()
    assert UserTestimonialsPage.can_create_at(course_page)
    testimonials_page = UserTestimonialsPageFactory.create(
        parent=course_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__title="image",
        items__0__testimonial__quote="quote",
    )
    assert course_page.testimonials == testimonials_page
    assert testimonials_page.heading == "heading"
    assert testimonials_page.subhead == "subhead"
    for testimonial in testimonials_page.items:  # pylint: disable=not-an-iterable
        assert testimonial.value.get("name") == "name"
        assert testimonial.value.get("title") == "title"
        assert testimonial.value.get("image").title == "image"
        assert testimonial.value.get("quote") == "quote"


def test_program_page_testimonials():
    """
    testimonials property should return expected value if associated with a ProgramPage
    """
    program_page = ProgramPageFactory.create()
    assert UserTestimonialsPage.can_create_at(program_page)
    testimonials_page = UserTestimonialsPageFactory.create(
        parent=program_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__title="image",
        items__0__testimonial__quote="quote",
    )
    assert program_page.testimonials == testimonials_page
    assert testimonials_page.heading == "heading"
    assert testimonials_page.subhead == "subhead"
    for testimonial in testimonials_page.items:  # pylint: disable=not-an-iterable
        assert testimonial.value.get("name") == "name"
        assert testimonial.value.get("title") == "title"
        assert testimonial.value.get("image").title == "image"
        assert testimonial.value.get("quote") == "quote"


def test_course_page_for_teams():
    """
    The ForTeams property should return expected values if associated with a CoursePage
    """
    course_page = CoursePageFactory.create()
    assert ForTeamsPage.can_create_at(course_page)
    teams_page = ForTeamsPageFactory.create(
        parent=course_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
    )
    assert course_page.for_teams == teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout
    assert teams_page.dark_theme


def test_program_page_for_teams():
    """
    The ForTeams property should return expected values if associated with a ProgramPage
    """
    program_page = ProgramPageFactory.create()
    assert ForTeamsPage.can_create_at(program_page)
    teams_page = ForTeamsPageFactory.create(
        parent=program_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
    )
    assert program_page.for_teams == teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout
    assert teams_page.dark_theme
    assert not ForTeamsPage.can_create_at(program_page)


def test_program_page_course_lineup():
    """
    course_lineup property should return expected values if associated with a ProgramPage
    """
    program_page = ProgramPageFactory.create()
    assert CoursesInProgramPage.can_create_at(program_page)
    courses_page = CoursesInProgramPageFactory.create(
        parent=program_page, heading="heading", body="<p>body</p>"
    )
    assert program_page.course_lineup == courses_page
    assert courses_page.heading == "heading"
    assert courses_page.body == "<p>body</p>"


def test_course_page_faq_property():
    """ Faqs property should return list of faqs related to given CoursePage"""
    course_page = CoursePageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(course_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=course_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is course_page
    assert list(course_page.faqs) == [faq]


def test_program_page_faq_property():
    """ Faqs property should return list of faqs related to given ProgramPage"""
    program_page = ProgramPageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(program_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=program_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is program_page
    assert list(program_page.faqs) == [faq]


def test_course_page_properties():
    """
    Wagtail-page-related properties should return expected values
    """
    course_page = CoursePageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        duration="1 week",
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert course_page.title == "<p>page title</p>"
    assert course_page.subhead == "subhead"
    assert course_page.description == "<p>desc</p>"
    assert course_page.duration == "1 week"
    assert course_page.video_title == "<p>title</p>"
    assert course_page.video_url == "http://test.com/mock.mp4"
    assert course_page.background_image.title == "background-image"


def test_program_page_properties():
    """
    Wagtail-page-related properties should return expected values if the Wagtail page exists
    """
    program_page = ProgramPageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        duration="1 week",
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert program_page.title == "<p>page title</p>"
    assert program_page.subhead == "subhead"
    assert program_page.description == "<p>desc</p>"
    assert program_page.duration == "1 week"
    assert program_page.video_title == "<p>title</p>"
    assert program_page.video_url == "http://test.com/mock.mp4"
    assert program_page.background_image.title == "background-image"


def test_course_page_learning_outcomes():
    """
    CoursePage related LearningOutcomesPage should return expected values if it exists
    """
    course_page = CoursePageFactory.create()

    assert course_page.outcomes is None
    assert LearningOutcomesPage.can_create_at(course_page)

    learning_outcomes_page = LearningOutcomesPageFactory(
        parent=course_page,
        heading="heading",
        sub_heading="subheading",
        outcome_items=json.dumps([{"type": "outcome", "value": "benefit"}]),
    )
    assert learning_outcomes_page.get_parent() == course_page
    assert learning_outcomes_page.heading == "heading"
    for (
        block
    ) in learning_outcomes_page.outcome_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "outcome"
        assert block.value == "benefit"
    assert course_page.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(course_page)


def test_program_learning_outcomes():
    """
    ProgramPage related LearningOutcomesPage should return expected values if it exists
    """
    program_page = ProgramPageFactory.create()

    assert LearningOutcomesPage.can_create_at(program_page)

    learning_outcomes_page = LearningOutcomesPageFactory(
        parent=program_page,
        heading="heading",
        sub_heading="subheading",
        outcome_items=json.dumps([{"type": "outcome", "value": "benefit"}]),
    )
    assert learning_outcomes_page.get_parent() == program_page
    assert learning_outcomes_page.heading == "heading"
    for (
        block
    ) in learning_outcomes_page.outcome_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "outcome"
        assert block.value == "benefit"
    assert program_page.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(program_page)


def test_course_page_learning_techniques():
    """
    CoursePage related subpages should return expected values if they exist
    CoursePage related LearningTechniquesPage should return expected values if it exists
    """
    course_page = CoursePageFactory.create()

    assert LearningTechniquesPage.can_create_at(course_page)
    learning_techniques_page = LearningTechniquesPageFactory(
        parent=course_page,
        technique_items__0__techniques__heading="heading",
        technique_items__0__techniques__sub_heading="sub_heading",
        technique_items__0__techniques__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == course_page
    for (
        technique
    ) in learning_techniques_page.technique_items:  # pylint: disable=not-an-iterable
        assert technique.value.get("heading") == "heading"
        assert technique.value.get("sub_heading") == "sub_heading"
        assert technique.value.get("image").title == "image-title"


def test_program_page_learning_techniques():
    """
    ProgramPage related subpages should return expected values if they exist
    ProgramPage related LearningTechniquesPage should return expected values if it exists
    """
    program_page = ProgramPageFactory.create(
        description="<p>desc</p>", duration="1 week"
    )

    assert LearningTechniquesPage.can_create_at(program_page)
    learning_techniques_page = LearningTechniquesPageFactory(
        parent=program_page,
        technique_items__0__techniques__heading="heading",
        technique_items__0__techniques__sub_heading="sub_heading",
        technique_items__0__techniques__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == program_page
    for (
        technique
    ) in learning_techniques_page.technique_items:  # pylint: disable=not-an-iterable
        assert technique.value.get("heading") == "heading"
        assert technique.value.get("sub_heading") == "sub_heading"
        assert technique.value.get("image").title == "image-title"


def test_program_page_who_should_enroll():
    """
    ProgramPage related WhoShouldEnrollPage should return expected values if it exists
    """
    program_page = ProgramPageFactory.create()

    assert WhoShouldEnrollPage.can_create_at(program_page)
    who_should_enroll_page = WhoShouldEnrollPageFactory.create(
        parent=program_page,
        content=json.dumps(
            [
                {"type": "item", "value": "<p>item</p>"},
                {"type": "item", "value": "<p>item</p>"},
            ]
        ),
    )
    assert who_should_enroll_page.get_parent() == program_page
    assert len(who_should_enroll_page.content) == 2
    for block in who_should_enroll_page.content:  # pylint: disable=not-an-iterable
        assert block.block_type == "item"
        assert block.value.source == "<p>item</p>"
    assert program_page.who_should_enroll == who_should_enroll_page
    assert not WhoShouldEnrollPage.can_create_at(program_page)


def test_course_page_propel_career():
    """
    The propel_career property should return expected values if associated with a CoursePage
    """
    course_page = CoursePageFactory.create()
    propel_career_page = TextSectionFactory.create(
        parent=course_page,
        content="<p>content</p>",
        dark_theme=True,
        action_title="Action Title",
    )
    assert course_page.propel_career == propel_career_page
    assert propel_career_page.action_title == "Action Title"
    assert propel_career_page.action_url
    assert propel_career_page.content == "<p>content</p>"
    assert propel_career_page.dark_theme


def test_program_page_propel_career():
    """
    The propel_career property should return expected values if associated with a ProgramPage
    """
    program_page = ProgramPageFactory.create()
    propel_career_page = TextSectionFactory.create(
        parent=program_page,
        content="<p>content</p>",
        dark_theme=True,
        action_title="Action Title",
    )
    assert program_page.propel_career == propel_career_page
    assert propel_career_page.action_title == "Action Title"
    assert propel_career_page.content == "<p>content</p>"
    assert propel_career_page.dark_theme

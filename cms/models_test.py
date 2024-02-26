""" Tests for cms pages. """
# pylint: disable=too-many-lines
import json
from datetime import date, datetime, timedelta

import factory
import pytest
from django.core.exceptions import ValidationError
from django.test.client import RequestFactory
from django.urls import resolve
from wagtail.coreutils import WAGTAIL_APPEND_SLASH

from cms.constants import (
    FORMAT_ONLINE,
    FORMAT_OTHER,
    ON_DEMAND_WEBINAR,
    ON_DEMAND_WEBINAR_BUTTON_TITLE,
    UPCOMING_WEBINAR,
    UPCOMING_WEBINAR_BUTTON_TITLE,
    WEBINAR_HEADER_BANNER,
)
from cms.factories import (
    CertificatePageFactory,
    CompaniesLogoCarouselPageFactory,
    CoursePageFactory,
    CoursesInProgramPageFactory,
    EnterprisePageFactory,
    ExternalCoursePageFactory,
    ExternalProgramPageFactory,
    FacultyMembersPageFactory,
    ForTeamsPageFactory,
    FrequentlyAskedQuestionFactory,
    FrequentlyAskedQuestionPageFactory,
    HomePageFactory,
    ImageCarouselPageFactory,
    LearningJourneyPageFactory,
    LearningOutcomesPageFactory,
    LearningStrategyFormPageFactory,
    LearningTechniquesPageFactory,
    NewsAndEventsPageFactory,
    ProgramFactory,
    ProgramPageFactory,
    ResourcePageFactory,
    SignatoryPageFactory,
    SiteNotificationFactory,
    SuccessStoriesPageFactory,
    TextSectionFactory,
    TextVideoSectionFactory,
    UserTestimonialsPageFactory,
    WebinarIndexPageFactory,
    WebinarPageFactory,
    WhoShouldEnrollPageFactory,
)
from cms.models import (
    CertificatePage,
    CoursesInProgramPage,
    ForTeamsPage,
    FrequentlyAskedQuestionPage,
    LearningJourneySection,
    LearningOutcomesPage,
    LearningTechniquesPage,
    SignatoryPage,
    UserTestimonialsPage,
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


def test_webinar_course():
    """
    Verify `course` property from the webinar page returns expected value
    """
    course = CourseFactory.create()
    webinar_page = WebinarPageFactory.create(course=course)
    assert webinar_page.course == course


def test_webinar_program():
    """
    Verify `program` property from the webinar page returns expected value
    """
    program = ProgramFactory.create()
    webinar_page = WebinarPageFactory.create(program=program)
    assert webinar_page.program == program


def test_webinar_context(staff_user):
    """
    Verify the context bring passed to the webinar_page.html
    """
    program_page = ProgramPageFactory.create()
    webinar_page = WebinarPageFactory.create(
        program=program_page.program, category=ON_DEMAND_WEBINAR
    )

    rf = RequestFactory()
    request = rf.get("/")
    request.user = staff_user
    context = webinar_page.get_context(request=request)

    assert context == {
        "self": webinar_page,
        "page": webinar_page,
        "request": request,
        "courseware_url": program_page.get_url(),
        "default_banner_image": WEBINAR_HEADER_BANNER,
        "detail_page_url": webinar_page.get_url(request=request),
    }


@pytest.mark.parametrize(
    "time, webinar_date,",
    (
        ["11 am", datetime.today() + timedelta(days=1)],
        [None, None],
    ),
)
def test_upcoming_webinar_date_time(time, webinar_date):
    """
    Verify `date` and `time` property for the upcoming webinar to be valid
    """

    if not time or not webinar_date:
        with pytest.raises(ValidationError):
            WebinarPageFactory.create(date=webinar_date, time=time)
    else:
        webinar = WebinarPageFactory.create(date=webinar_date, time=time)
        assert webinar.category == UPCOMING_WEBINAR
        assert webinar.time == "11 am"
        assert isinstance(webinar.date, date)


def test_on_demand_webinar_fields():
    """
    Verify essential on-demand webinar fields.
    """
    course = CourseFactory.create()
    webinar_index = WebinarIndexPageFactory.create()
    webinar = WebinarPageFactory.create(
        category=ON_DEMAND_WEBINAR, parent=webinar_index, course=course
    )
    assert webinar.category == ON_DEMAND_WEBINAR
    assert webinar.course == course


def test_is_upcoming_webinar():
    """
    Tests `is_upcoming_webinar` property from the webinar page.
    """
    webinar_index = WebinarIndexPageFactory.create()
    ondemand_webinar = WebinarPageFactory.create(
        category=ON_DEMAND_WEBINAR, parent=webinar_index
    )
    assert not ondemand_webinar.is_upcoming_webinar
    upcoming_webinar = WebinarPageFactory.create(
        category=UPCOMING_WEBINAR, parent=webinar_index
    )
    assert upcoming_webinar.is_upcoming_webinar


def test_webinar_detail_page_button_title():
    """
    Tests `detail_page_button_title` property from the webinar page.
    """
    webinar_index = WebinarIndexPageFactory.create()
    ondemand_webinar = WebinarPageFactory.create(
        category=ON_DEMAND_WEBINAR, parent=webinar_index
    )
    assert ondemand_webinar.detail_page_button_title == ON_DEMAND_WEBINAR_BUTTON_TITLE
    upcoming_webinar = WebinarPageFactory.create(
        category=UPCOMING_WEBINAR, parent=webinar_index
    )
    assert upcoming_webinar.detail_page_button_title == UPCOMING_WEBINAR_BUTTON_TITLE


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


def test_program_page_course_pages_live_only():
    """
    Verify `course_pages` property from the program page returns only live course pages
    """
    program_page = ProgramPageFactory.create()
    assert list(program_page.course_pages) == []
    course_pages = CoursePageFactory.create_batch(
        2, course__program=program_page.program
    )
    # The below page should not be included in course pages
    CoursePageFactory.create(course__program=program_page.program, live=False)
    assert list(program_page.course_pages) == course_pages


def test_custom_detail_page_urls():
    """Verify that course/external-course/program detail pages return our custom URL path"""
    readable_id = "some:readable-id"
    external_readable_id = "some:external-readable-id"
    program_pages = ProgramPageFactory.create_batch(
        2, program__readable_id=factory.Iterator([readable_id, "non-matching-id"])
    )
    external_program_pages = ExternalProgramPageFactory.create_batch(
        2,
        program__readable_id=factory.Iterator(
            [external_readable_id, "non-matching-external-id"]
        ),
    )
    course_pages = CoursePageFactory.create_batch(
        2, course__readable_id=factory.Iterator([readable_id, "non-matching-id"])
    )
    external_course_pages = ExternalCoursePageFactory.create_batch(
        2,
        course__readable_id=factory.Iterator(
            [external_readable_id, "non-matching-external-id"]
        ),
    )
    assert program_pages[0].get_url() == "/programs/{}/".format(readable_id)
    assert external_program_pages[0].get_url() == "/programs/{}/".format(
        external_readable_id
    )
    assert course_pages[0].get_url() == "/courses/{}/".format(readable_id)
    assert external_course_pages[0].get_url() == "/courses/{}/".format(
        external_readable_id
    )


def test_custom_detail_page_urls_handled():
    """Verify that custom URL paths for our course/program are served by the standard Wagtail view"""
    readable_id = "some:readable-id"
    CoursePageFactory.create(course__readable_id=readable_id)
    resolver_match = resolve("/courses/{}/".format(readable_id))
    assert (
        resolver_match.func.__module__ == "wagtail.views"
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

    del home_page.child_pages

    testimonials_page = UserTestimonialsPageFactory.create(
        parent=home_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__image__title="image",
        items__0__testimonial__quote="quote",
        items__1__testimonial__name="name",
        items__1__testimonial__title="title",
        items__1__testimonial__image__image__title="image",
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


def test_home_page_news_and_events():
    """
    NewsAndEvents subpage should provide expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.news_and_events

    del home_page.child_pages

    news_and_events_page = create_news_and_events(parent=home_page)
    assert home_page.news_and_events == news_and_events_page
    assert news_and_events_page.heading == "heading"
    for count, news_and_events in enumerate(news_and_events_page.items):
        assert news_and_events.value.get("content_type") == f"content_type-{count}"
        assert news_and_events.value.get("title") == f"title-{count}"
        assert news_and_events.value.get("image").title == f"image-{count}"
        assert news_and_events.value.get("content") == f"content-{count}"
        assert news_and_events.value.get("call_to_action") == f"call_to_action-{count}"
        assert news_and_events.value.get("action_url") == f"action_url-{count}"


def test_home_page_inquiry_section():
    """
    inquiry_section property should return expected values
    """
    home_page = HomePageFactory.create()
    assert not home_page.inquiry_section

    del home_page.child_pages

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

    del home_page.child_pages

    course = CourseFactory.create(page=None)
    page = CoursePageFactory(course=course)
    carousel_page = CoursesInProgramPageFactory.create(
        parent=home_page,
        heading="heading",
        body="<p>body</p>",
        override_contents=True,
        contents__0__item__page=page,
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

    del home_page.child_pages

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

    del home_page.child_pages

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


def test_external_program_page_faculty_subpage():
    """
    FacultyMembersPage should return expected values if associated with ExternalProgramPage
    """
    external_program_page = ExternalProgramPageFactory.create()

    assert not external_program_page.faculty
    FacultyMembersPageFactory.create(
        parent=external_program_page, members=json.dumps(_get_faculty_members())
    )
    _assert_faculty_members(external_program_page)


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


def test_external_course_page_faculty_subpage():
    """
    FacultyMembersPage should return expected values if associated with ExternalCoursePage
    """
    external_course_page = ExternalCoursePageFactory.create()

    assert not external_course_page.faculty
    FacultyMembersPageFactory.create(
        parent=external_course_page, members=json.dumps(_get_faculty_members())
    )
    _assert_faculty_members(external_course_page)


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
    # invalidate cached property
    del obj.child_pages

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
        items__0__testimonial__image__image__title="image",
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


def test_external_course_page_testimonials():
    """
    testimonials property should return expected value if associated with an ExternalCoursePage
    """
    external_course_page = ExternalCoursePageFactory.create()
    assert UserTestimonialsPage.can_create_at(external_course_page)
    testimonials_page = UserTestimonialsPageFactory.create(
        parent=external_course_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__image__title="image",
        items__0__testimonial__quote="quote",
    )
    assert external_course_page.testimonials == testimonials_page
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
        items__0__testimonial__image__image__title="image",
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


def test_external_program_page_testimonials():
    """
    testimonials property should return expected value if associated with an ExternalProgramPage
    """
    external_program_page = ExternalProgramPageFactory.create()
    assert UserTestimonialsPage.can_create_at(external_program_page)
    testimonials_page = UserTestimonialsPageFactory.create(
        parent=external_program_page,
        heading="heading",
        subhead="subhead",
        items__0__testimonial__name="name",
        items__0__testimonial__title="title",
        items__0__testimonial__image__image__title="image",
        items__0__testimonial__quote="quote",
    )
    assert external_program_page.testimonials == testimonials_page
    assert testimonials_page.heading == "heading"
    assert testimonials_page.subhead == "subhead"
    for testimonial in testimonials_page.items:  # pylint: disable=not-an-iterable
        assert testimonial.value.get("name") == "name"
        assert testimonial.value.get("title") == "title"
        assert testimonial.value.get("image").title == "image"
        assert testimonial.value.get("quote") == "quote"


def test_child_page_unroutable():
    """
    Child page should not provide a URL if it unroutable
    """
    home_page = HomePageFactory.create()
    child_page = TextSectionFactory.create(parent=home_page)
    assert not child_page.get_full_url()


def test_program_page_child_page_url():
    """
    The live URL of child pages should be of the correct format:
    <site_root>/programs/<program__readable_id>/<child_page__slug>
    """
    program_page = ProgramPageFactory.create(program__readable_id="program:test")
    child_page = TextSectionFactory.create(parent=program_page)

    program_page_url = program_page.get_full_url()
    child_page_url = child_page.get_full_url()

    if WAGTAIL_APPEND_SLASH:
        assert child_page_url == "{}{}/".format(program_page_url, child_page.slug)
    else:
        assert child_page_url == "{}/{}".format(program_page_url, child_page.slug)


def test_course_page_child_page_url():
    """
    The live URL of child pages should be of the correct format:
    <site_root>/courses/<course__readable_id>/<child_page__slug>
    """
    course_page = CoursePageFactory.create(course__readable_id="course:test")
    child_page = TextSectionFactory.create(parent=course_page)

    course_page_url = course_page.get_full_url()
    child_page_url = child_page.get_full_url()

    if WAGTAIL_APPEND_SLASH:
        assert child_page_url == "{}{}/".format(course_page_url, child_page.slug)
    else:
        assert child_page_url == "{}/{}".format(course_page_url, child_page.slug)


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


def test_external_course_page_for_teams():
    """
    The ForTeams property should return expected values if associated with a ExternalCoursePage
    """
    external_course_page = ExternalCoursePageFactory.create()
    assert ForTeamsPage.can_create_at(external_course_page)
    teams_page = ForTeamsPageFactory.create(
        parent=external_course_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
    )
    assert external_course_page.for_teams == teams_page
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


def test_external_program_page_for_teams():
    """
    The ForTeams property should return expected values if associated with an ExternalProgramPage
    """
    external_program_page = ExternalProgramPageFactory.create()
    assert ForTeamsPage.can_create_at(external_program_page)
    teams_page = ForTeamsPageFactory.create(
        parent=external_program_page,
        content="<p>content</p>",
        switch_layout=True,
        dark_theme=True,
        action_title="Action Title",
    )
    assert external_program_page.for_teams == teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout
    assert teams_page.dark_theme


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
    """Faqs property should return list of faqs related to given CoursePage"""
    course_page = CoursePageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(course_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=course_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is course_page
    assert list(course_page.faqs) == [faq]


def test_external_course_page_faq_property():
    """Faqs property should return list of faqs related to given ExternalCoursePage"""
    external_course_page = ExternalCoursePageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(external_course_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=external_course_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is external_course_page
    assert list(external_course_page.faqs) == [faq]


def test_program_page_faq_property():
    """Faqs property should return list of faqs related to given ProgramPage"""
    program_page = ProgramPageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(program_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=program_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is program_page
    assert list(program_page.faqs) == [faq]


def test_external_program_page_faq_property():
    """Faqs property should return list of faqs related to given ExternalProgramPage"""
    external_program_page = ExternalProgramPageFactory.create()
    assert FrequentlyAskedQuestionPage.can_create_at(external_program_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=external_program_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is external_program_page
    assert list(external_program_page.faqs) == [faq]


def test_course_page_properties():
    """
    Wagtail-page-related properties should return expected values
    """
    course_page = CoursePageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        catalog_details="<p>catalog desc</p>",
        duration="1 week",
        format=FORMAT_ONLINE,
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert course_page.title == "<p>page title</p>"
    assert course_page.subhead == "subhead"
    assert course_page.description == "<p>desc</p>"
    assert course_page.catalog_details == "<p>catalog desc</p>"
    assert course_page.duration == "1 week"
    assert course_page.format == FORMAT_ONLINE
    assert course_page.video_title == "<p>title</p>"
    assert course_page.video_url == "http://test.com/mock.mp4"
    assert course_page.background_image.title == "background-image"


def test_external_course_page_properties():
    """
    Wagtail-page-related properties should return expected values
    """
    external_course_page = ExternalCoursePageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        catalog_details="<p>catalog desc</p>",
        duration="1 week",
        format=FORMAT_OTHER,
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )

    assert external_course_page.title == "<p>page title</p>"
    assert external_course_page.subhead == "subhead"
    assert external_course_page.description == "<p>desc</p>"
    assert external_course_page.catalog_details == "<p>catalog desc</p>"
    assert external_course_page.duration == "1 week"
    assert external_course_page.format == FORMAT_OTHER
    assert external_course_page.video_title == "<p>title</p>"
    assert external_course_page.video_url == "http://test.com/mock.mp4"
    assert external_course_page.background_image.title == "background-image"
    assert external_course_page.program_page == external_course_page.course.program.page
    assert not external_course_page.course_lineup
    assert external_course_page.course_pages
    assert external_course_page.product == external_course_page.course


def test_course_page_format_field_default_value():
    """
    Verifies that the "format" field in a course page has the default value FORMAT_ONLINE.
    """
    course_page = CoursePageFactory.create()

    assert course_page.format == FORMAT_ONLINE


@pytest.mark.parametrize("course_format", [FORMAT_ONLINE, FORMAT_OTHER])
def test_course_page_format_field_choices(course_format, staff_user):
    """
    Verifies that if the "format" field in a course page contains the values FORMAT_ONLINE and FORMAT_OTHER,
    and they are in the same context.
    """
    course_page = CoursePageFactory.create(format=course_format)

    rf = RequestFactory()
    request = rf.get("/")
    request.user = staff_user

    context = course_page.get_context(request=request)
    context_format = context.get("page").format

    assert context_format == course_format


def test_program_page_properties():
    """
    Wagtail-page-related properties should return expected values if the Wagtail page exists
    """
    program_page = ProgramPageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        catalog_details="<p>catalog desc</p>",
        duration="1 week",
        format=FORMAT_ONLINE,
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert program_page.title == "<p>page title</p>"
    assert program_page.subhead == "subhead"
    assert program_page.description == "<p>desc</p>"
    assert program_page.catalog_details == "<p>catalog desc</p>"
    assert program_page.duration == "1 week"
    assert program_page.format == FORMAT_ONLINE
    assert program_page.video_title == "<p>title</p>"
    assert program_page.video_url == "http://test.com/mock.mp4"
    assert program_page.background_image.title == "background-image"


def test_external_program_page_properties():
    """
    Wagtail-page-related properties for ExternalProgramPage should return expected values
    """
    external_program_page = ExternalProgramPageFactory.create(
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        catalog_details="<p>catalog desc</p>",
        duration="1 week",
        format=FORMAT_OTHER,
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )

    assert external_program_page.title == "<p>page title</p>"
    assert external_program_page.subhead == "subhead"
    assert external_program_page.description == "<p>desc</p>"
    assert external_program_page.catalog_details == "<p>catalog desc</p>"
    assert external_program_page.duration == "1 week"
    assert external_program_page.format == FORMAT_OTHER
    assert external_program_page.video_title == "<p>title</p>"
    assert external_program_page.video_url == "http://test.com/mock.mp4"
    assert external_program_page.background_image.title == "background-image"


def test_program_page_format_field_default_value():
    """
    Verifies that the "format" field in a program page has the default value FORMAT_ONLINE.
    """
    program_page = ProgramPageFactory.create()

    assert program_page.format == FORMAT_ONLINE


@pytest.mark.parametrize("program_format", [FORMAT_ONLINE, FORMAT_OTHER])
def test_program_page_format_field_choices(program_format, staff_user):
    """
    Verifies that if the "format" field in a program page contains the values FORMAT_ONLINE and FORMAT_OTHER,
    and they are in the same context.
    """
    program_page = ProgramPageFactory.create(format=program_format)

    rf = RequestFactory()
    request = rf.get("/")
    request.user = staff_user

    context = program_page.get_context(request=request)
    context_format = context.get("page").format

    assert context_format == program_format


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
        sub_heading="<p>subheading</p>",
        outcome_items=json.dumps([{"type": "outcome", "value": "benefit"}]),
    )
    assert learning_outcomes_page.get_parent() == course_page
    assert learning_outcomes_page.heading == "heading"
    assert learning_outcomes_page.sub_heading == "<p>subheading</p>"
    for (
        block
    ) in learning_outcomes_page.outcome_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "outcome"
        assert block.value == "benefit"

    # invalidate cached property
    del course_page.child_pages

    assert course_page.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(course_page)


def test_external_course_page_learning_outcomes():
    """
    ExternalCoursePage related LearningOutcomesPage should return expected values if it exists
    """
    external_course_page = ExternalCoursePageFactory.create()

    assert external_course_page.outcomes is None
    assert LearningOutcomesPage.can_create_at(external_course_page)

    learning_outcomes_page = LearningOutcomesPageFactory(
        parent=external_course_page,
        heading="heading",
        sub_heading="<p>subheading</p>",
        outcome_items=json.dumps([{"type": "outcome", "value": "benefit"}]),
    )
    assert learning_outcomes_page.get_parent() == external_course_page
    assert learning_outcomes_page.heading == "heading"
    assert learning_outcomes_page.sub_heading == "<p>subheading</p>"
    for (
        block
    ) in learning_outcomes_page.outcome_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "outcome"
        assert block.value == "benefit"

    # invalidate cached property
    del external_course_page.child_pages

    assert external_course_page.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(external_course_page)


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


def test_external_program_learning_outcomes():
    """
    ExternalProgramPage related LearningOutcomesPage should return expected values if it exists
    """
    external_program_page = ExternalProgramPageFactory.create()

    assert LearningOutcomesPage.can_create_at(external_program_page)

    learning_outcomes_page = LearningOutcomesPageFactory(
        parent=external_program_page,
        heading="heading",
        sub_heading="subheading",
        outcome_items=json.dumps([{"type": "outcome", "value": "benefit"}]),
    )
    assert learning_outcomes_page.get_parent() == external_program_page
    assert learning_outcomes_page.heading == "heading"
    for (
        block
    ) in learning_outcomes_page.outcome_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "outcome"
        assert block.value == "benefit"
    assert external_program_page.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(external_program_page)


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
        technique_items__0__techniques__image__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == course_page
    for (
        technique
    ) in learning_techniques_page.technique_items:  # pylint: disable=not-an-iterable
        assert technique.value.get("heading") == "heading"
        assert technique.value.get("sub_heading") == "sub_heading"
        assert technique.value.get("image").title == "image-title"


def test_external_course_page_learning_techniques():
    """
    ExternalCoursePage related subpages should return expected values if they exist
    ExternalCoursePage related LearningTechniquesPage should return expected values if it exists
    """
    external_course_page = ExternalCoursePageFactory.create()

    assert LearningTechniquesPage.can_create_at(external_course_page)
    learning_techniques_page = LearningTechniquesPageFactory(
        parent=external_course_page,
        technique_items__0__techniques__heading="heading",
        technique_items__0__techniques__sub_heading="sub_heading",
        technique_items__0__techniques__image__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == external_course_page
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
        technique_items__0__techniques__image__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == program_page
    for (
        technique
    ) in learning_techniques_page.technique_items:  # pylint: disable=not-an-iterable
        assert technique.value.get("heading") == "heading"
        assert technique.value.get("sub_heading") == "sub_heading"
        assert technique.value.get("image").title == "image-title"


def test_external_program_page_learning_techniques():
    """
    ExternalProgramPage related subpages should return expected values if they exist
    ExternalProgramPage related LearningTechniquesPage should return expected values if it exists
    """
    external_program_page = ExternalProgramPageFactory.create(
        description="<p>desc</p>", duration="1 week"
    )

    assert LearningTechniquesPage.can_create_at(external_program_page)
    learning_techniques_page = LearningTechniquesPageFactory(
        parent=external_program_page,
        technique_items__0__techniques__heading="heading",
        technique_items__0__techniques__sub_heading="sub_heading",
        technique_items__0__techniques__image__image__title="image-title",
    )
    assert learning_techniques_page.get_parent() == external_program_page
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

    # default page hedding
    assert who_should_enroll_page.heading == "Who Should Enroll"

    # test that it can be modified
    new_heading = "New heading of the page"
    who_should_enroll_page.heading = new_heading
    who_should_enroll_page.save()

    assert who_should_enroll_page.heading == new_heading


def test_external_program_page_who_should_enroll():
    """
    ExternalProgramPage related WhoShouldEnrollPage should return expected values if it exists
    """
    external_program_page = ExternalProgramPageFactory.create()

    assert WhoShouldEnrollPage.can_create_at(external_program_page)
    who_should_enroll_page = WhoShouldEnrollPageFactory.create(
        parent=external_program_page,
        content=json.dumps(
            [
                {"type": "item", "value": "<p>item</p>"},
                {"type": "item", "value": "<p>item</p>"},
            ]
        ),
    )
    assert who_should_enroll_page.get_parent() == external_program_page
    assert len(who_should_enroll_page.content) == 2
    for block in who_should_enroll_page.content:  # pylint: disable=not-an-iterable
        assert block.block_type == "item"
        assert block.value.source == "<p>item</p>"
    assert external_program_page.who_should_enroll == who_should_enroll_page
    assert not WhoShouldEnrollPage.can_create_at(external_program_page)

    # default page hedding
    assert who_should_enroll_page.heading == "Who Should Enroll"

    # test that it can be modified
    new_heading = "New heading of the page"
    who_should_enroll_page.heading = new_heading
    who_should_enroll_page.save()

    assert who_should_enroll_page.heading == new_heading


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


def test_external_course_page_propel_career():
    """
    The propel_career property should return expected values if associated with an ExternalCoursePage
    """
    external_course_page = ExternalCoursePageFactory.create()
    propel_career_page = TextSectionFactory.create(
        parent=external_course_page,
        content="<p>content</p>",
        dark_theme=True,
        action_title="Action Title",
    )
    assert external_course_page.propel_career == propel_career_page
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


def test_external_program_page_propel_career():
    """
    The propel_career property should return expected values if associated with a ExternalProgramPage
    """
    external_program_page = ExternalProgramPageFactory.create()
    propel_career_page = TextSectionFactory.create(
        parent=external_program_page,
        content="<p>content</p>",
        dark_theme=True,
        action_title="Action Title",
    )
    assert external_program_page.propel_career == propel_career_page
    assert propel_career_page.action_title == "Action Title"
    assert propel_career_page.content == "<p>content</p>"
    assert propel_career_page.dark_theme


def test_is_course_page():
    """Returns True if object is type of CoursePage"""
    program_page = ProgramPageFactory.create()
    course_page = CoursePageFactory.create()

    assert not program_page.is_course_page
    assert course_page.is_course_page


def test_is_external_course_page():
    """Returns True if object is type of ExternalCoursePage"""
    program_page = ProgramPageFactory.create()
    course_page = CoursePageFactory.create()
    external_course_page = ExternalCoursePageFactory.create()

    assert not program_page.is_external_course_page
    assert not course_page.is_external_course_page
    assert external_course_page.is_external_course_page


def test_is_external_program_page():
    """Returns True if object is type of ExternalProgramPage"""
    external_program_page = ExternalProgramPageFactory.create()
    assert external_program_page.is_external_program_page


def test_featured_product():
    """Verify that there will be only one product marked as feature."""
    program_page = ProgramPageFactory.create(featured=True)
    another_program_page = ProgramPageFactory.create(featured=True)

    program_page.refresh_from_db()
    assert not program_page.featured
    assert another_program_page.featured

    # add and mark course as featured
    course_page = CoursePageFactory.create(featured=True)
    another_program_page.refresh_from_db()
    assert not another_program_page.featured
    assert course_page.featured

    another_course_page = CoursePageFactory.create(featured=True)
    course_page.refresh_from_db()
    assert not course_page.featured
    assert another_course_page.featured

    external_course_page = ExternalCoursePageFactory.create(featured=True)
    another_course_page.refresh_from_db()
    assert not another_course_page.featured
    assert external_course_page.featured

    external_program_page = ExternalProgramPageFactory.create(featured=True)
    external_course_page.refresh_from_db()
    assert not external_course_page.featured
    assert external_program_page.featured


def test_certificate_for_course_page():
    """
    The Certificate property should return expected values if associated with a CertificatePage
    """
    course_page = CoursePageFactory.create(certificate_page=None)
    assert CertificatePage.can_create_at(course_page)
    assert not SignatoryPage.can_create_at(course_page)

    signatory = SignatoryPageFactory(
        name="Name",
        title_1="Title_1",
        title_2="Title_2",
        organization="Organization",
        signature_image__image__title="Image",
    )
    certificate_page = CertificatePageFactory.create(
        parent=course_page,
        product_name="product_name",
        CEUs="1.8",
        partner_logo__image__title="Partner Logo",
        signatories__0__signatory__page=signatory,
    )
    assert certificate_page.get_parent() == course_page
    assert certificate_page.CEUs == "1.8"
    assert certificate_page.product_name == "product_name"
    assert certificate_page.partner_logo.title == "Partner Logo"
    for signatory in certificate_page.signatories:  # pylint: disable=not-an-iterable
        assert signatory.value.name == "Name"
        assert signatory.value.title_1 == "Title_1"
        assert signatory.value.title_2 == "Title_2"
        assert signatory.value.organization == "Organization"
        assert signatory.value.signature_image.title == "Image"


def test_certificate_for_program_page():
    """
    The Certificate property should return expected values if associated with a CertificatePage
    """
    program_page = ProgramPageFactory.create(certificate_page=None)
    assert CertificatePage.can_create_at(program_page)
    assert not SignatoryPage.can_create_at(program_page)

    signatory = SignatoryPageFactory(
        name="Name",
        title_1="Title_1",
        title_2="Title_2",
        organization="Organization",
        signature_image__image__title="Image",
    )

    certificate_page = CertificatePageFactory.create(
        parent=program_page,
        product_name="product_name",
        CEUs="2.8",
        partner_logo__image__title="Partner Logo",
        signatories__0__signatory__page=signatory,
    )

    assert certificate_page.get_parent() == program_page
    assert certificate_page.CEUs == "2.8"
    assert certificate_page.product_name == "product_name"
    assert certificate_page.partner_logo.title == "Partner Logo"
    for signatory in certificate_page.signatories:  # pylint: disable=not-an-iterable
        assert signatory.value.name == "Name"
        assert signatory.value.title_1 == "Title_1"
        assert signatory.value.title_2 == "Title_2"
        assert signatory.value.organization == "Organization"
        assert signatory.value.signature_image.title == "Image"


def test_program_course_order():
    """
    The course pages in program page should be ordered on the basis of position_in_program
    """
    program_page = ProgramPageFactory.create()
    course_pages = CoursePageFactory.create_batch(
        3,
        course__position_in_program=factory.Iterator([2, 3, 1]),
        course__program=program_page.program,
    )
    single_course_page = course_pages[0]
    assert [
        course_page.course.position_in_program
        for course_page in single_course_page.course_pages
    ] == [1, 2, 3]
    assert [
        course_page.course.position_in_program
        for course_page in program_page.course_pages
    ] == [1, 2, 3]


def test_product_program_page_news_and_events():
    """
    NewsAndEvents subpage should provide expected values if comes under ProgramPage.
    """
    program_page = ProgramPageFactory.create()
    assert not program_page.news_and_events
    news_and_events_page = create_news_and_events(parent=program_page)

    # invalidate cached property
    del program_page.child_pages

    assert program_page.news_and_events == news_and_events_page
    assert news_and_events_page.heading == "heading"
    _assert_news_and_events_values(news_and_events_page)


def test_product_course_page_news_and_events_without_program():
    """
    NewsAndEvents subpage should provide expected values if comes under CoursePage
    and CoursePage is not associated with any program.
    """
    course_page = CoursePageFactory.create(course__program=None)
    assert not course_page.news_and_events
    news_and_events_page = create_news_and_events(parent=course_page)

    # invalidate cached property
    del course_page.child_pages

    assert course_page.news_and_events == news_and_events_page
    assert news_and_events_page.heading == "heading"
    _assert_news_and_events_values(news_and_events_page)


def test_product_course_page_news_and_events_with_program():
    """
    NewsAndEvents subpage should provide expected values of program 'news and events' if comes under CoursePage
    and CoursePage is associated with a program.
    """
    program_page = ProgramPageFactory.create()
    course_page = CoursePageFactory.create(course__program=program_page.program)
    assert not course_page.news_and_events
    program_news_and_events_page = create_news_and_events(
        parent=program_page, heading="heading program"
    )
    course_news_and_events_page = create_news_and_events(parent=course_page)

    # invalidate cached property
    del course_page.child_pages
    del course_page.program_page.child_pages

    assert course_page.news_and_events == program_news_and_events_page
    assert course_page.news_and_events != course_news_and_events_page
    assert program_news_and_events_page.heading == "heading program"
    _assert_news_and_events_values(program_news_and_events_page)


def test_external_program_page_news_and_events():
    """
    NewsAndEvents subpage should provide expected values of external program.
    """
    external_program_page = ExternalProgramPageFactory.create()
    assert not external_program_page.news_and_events
    news_and_events_page = create_news_and_events(parent=external_program_page)

    # invalidate cached property
    del external_program_page.child_pages

    assert external_program_page.news_and_events == news_and_events_page
    assert news_and_events_page.heading == "heading"
    _assert_news_and_events_values(news_and_events_page)


def test_external_course_page_news_and_events():
    """
    NewsAndEvents subpage should provide expected values of external course.
    """
    external_course_page = ExternalCoursePageFactory.create()
    assert not external_course_page.news_and_events
    news_and_events_page = create_news_and_events(parent=external_course_page)

    # invalidate cached property
    del external_course_page.child_pages

    assert external_course_page.news_and_events == news_and_events_page
    assert news_and_events_page.heading == "heading"
    _assert_news_and_events_values(news_and_events_page)


def create_news_and_events(parent, heading="heading"):
    """
    Create a news and events page and return it.
    """
    return NewsAndEventsPageFactory.create(
        parent=parent,
        heading=heading,
        items__0__news_and_events__content_type="content_type-0",
        items__0__news_and_events__title="title-0",
        items__0__news_and_events__image__image__title="image-0",
        items__0__news_and_events__content="content-0",
        items__0__news_and_events__call_to_action="call_to_action-0",
        items__0__news_and_events__action_url="action_url-0",
        items__1__news_and_events__content_type="content_type-1",
        items__1__news_and_events__title="title-1",
        items__1__news_and_events__image__image__title="image-1",
        items__1__news_and_events__content="content-1",
        items__1__news_and_events__call_to_action="call_to_action-1",
        items__1__news_and_events__action_url="action_url-1",
    )


def _assert_news_and_events_values(news_and_events_page):
    """
    Assure the expected values for news and events page.
    """
    for count, news_and_events in enumerate(news_and_events_page.items):
        assert news_and_events.value.get("content_type") == f"content_type-{count}"
        assert news_and_events.value.get("title") == f"title-{count}"
        assert news_and_events.value.get("image").title == f"image-{count}"
        assert news_and_events.value.get("content") == f"content-{count}"
        assert news_and_events.value.get("call_to_action") == f"call_to_action-{count}"
        assert news_and_events.value.get("action_url") == f"action_url-{count}"


def test_enterprise_page_companies_logo_carousel():
    """
    companies_logo_carousel property should return expected values.
    """

    enterprise_page = EnterprisePageFactory.create(
        action_title="title", description="description"
    )
    assert not enterprise_page.companies_logo_carousel

    del enterprise_page.child_pages

    companies_logo_carousel = CompaniesLogoCarouselPageFactory.create(
        parent=enterprise_page,
        heading="heading",
        images__0__image__image__title="image-title-0",
        images__1__image__image__title="image-title-1",
        images__2__image__image__title="image-title-2",
        images__3__image__image__title="image-title-3",
    )

    assert enterprise_page.companies_logo_carousel == companies_logo_carousel
    assert companies_logo_carousel.heading == "heading"

    for index, image in enumerate(companies_logo_carousel.images):
        assert image.value.title == "image-title-{}".format(index)


def test_enterprise_page_learning_journey():
    """
    LearningJourneyPage should return expected values if it exists
    """

    enterprise_page = EnterprisePageFactory.create(
        action_title="title", description="description"
    )

    assert not enterprise_page.learning_journey
    assert LearningJourneySection.can_create_at(enterprise_page)

    learning_journey = LearningJourneyPageFactory(
        parent=enterprise_page,
        heading="heading",
        description="description",
        journey_items=json.dumps([{"type": "journey", "value": "value"}]),
        journey_image__title="background-image",
    )

    assert learning_journey.get_parent() == enterprise_page
    assert learning_journey.heading == "heading"
    assert learning_journey.description == "description"

    for block in learning_journey.journey_items:  # pylint: disable=not-an-iterable
        assert block.block_type == "journey"
        assert block.value == "value"

    assert learning_journey.action_url
    assert learning_journey.pdf_file

    del enterprise_page.child_pages

    assert enterprise_page.learning_journey == learning_journey
    assert not LearningOutcomesPage.can_create_at(enterprise_page)


def test_enterprise_page_success_stories():
    """
    SuccessStories subpage should provide expected values
    """

    enterprise_page = EnterprisePageFactory.create(
        action_title="title", description="description"
    )

    assert not enterprise_page.success_stories_carousel
    del enterprise_page.child_pages

    success_stories_carousel = SuccessStoriesPageFactory.create(
        parent=enterprise_page,
        heading="heading",
        subhead="subhead",
        success_stories__0__success_story__title="title",
        success_stories__0__success_story__image__image__title="image",
        success_stories__0__success_story__content="content",
        success_stories__0__success_story__call_to_action="call_to_action",
        success_stories__0__success_story__action_url="action_url",
        success_stories__1__success_story__title="title",
        success_stories__1__success_story__image__image__title="image",
        success_stories__1__success_story__content="content",
        success_stories__1__success_story__call_to_action="call_to_action",
        success_stories__1__success_story__action_url="action_url",
    )

    assert enterprise_page.success_stories_carousel == success_stories_carousel
    assert success_stories_carousel.heading == "heading"
    assert success_stories_carousel.subhead == "subhead"

    for success_stories in success_stories_carousel.success_stories:
        assert success_stories.value.get("title") == "title"
        assert success_stories.value.get("image").title == "image"
        assert success_stories.value.get("content") == "content"
        assert success_stories.value.get("call_to_action") == "call_to_action"
        assert success_stories.value.get("action_url") == "action_url"


def test_enterprise_page_learning_strategy_form():
    """
    LearningStrategyForm subpage should provide expected values
    """

    enterprise_page = EnterprisePageFactory.create(
        action_title="title", description="description"
    )

    assert not enterprise_page.learning_strategy_form
    del enterprise_page.child_pages

    learning_strategy_form = LearningStrategyFormPageFactory.create(
        parent=enterprise_page,
        heading="heading",
        subhead="subhead",
        consent="consent",
    )

    assert enterprise_page.learning_strategy_form == learning_strategy_form
    assert learning_strategy_form.heading == "heading"
    assert learning_strategy_form.subhead == "subhead"
    assert learning_strategy_form.consent == "consent"

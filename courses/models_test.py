"""Tests for course models"""
from datetime import timedelta

import json
import pytest
import factory

from courses.factories import ProgramFactory, CourseFactory, CourseRunFactory
from ecommerce.factories import ProductFactory, ProductVersionFactory
from cms.factories import (
    ProgramPageFactory,
    CoursePageFactory,
    LearningOutcomesPageFactory,
    LearningTechniquesPageFactory,
    FrequentlyAskedQuestionFactory,
    FrequentlyAskedQuestionPageFactory,
    ForTeamsPageFactory,
)

from cms.models import (
    LearningOutcomesPage,
    LearningTechniquesPage,
    FrequentlyAskedQuestionPage,
    ForTeamsPage,
)
from mitxpro.utils import now_in_utc

pytestmark = [pytest.mark.django_db]


def test_program_course_auto_position():
    """
    If a course is added to a program with no position specified, it should be given the last position
    """
    first_course = CourseFactory.create(position_in_program=None)
    assert first_course.position_in_program == 1
    second_course = CourseFactory.create(
        program=first_course.program, position_in_program=None
    )
    assert second_course.position_in_program == 2


def test_program_num_courses():
    """
    Program should return number of courses associated with it
    """
    program = ProgramFactory.create()
    assert program.num_courses == 0

    CourseFactory.create(program=program)
    assert program.num_courses == 1

    CourseFactory.create(program=program)
    assert program.num_courses == 2


def test_program_next_run_date():
    """
    next_run_date should return the date of the CourseRun with the nearest future start date
    """
    program = ProgramFactory.create()
    CourseRunFactory.create_batch(2, course__program=program, past_start=True)
    assert program.next_run_date is None

    now = now_in_utc()
    future_dates = [now + timedelta(hours=1), now + timedelta(hours=2)]
    CourseRunFactory.create_batch(
        2, course__program=program, start_date=factory.Iterator(future_dates)
    )
    assert program.next_run_date == future_dates[0]


def test_program_current_price():
    """
    current_price should return the price of the latest product version if it exists
    """
    program = ProgramFactory.create()
    assert program.current_price is None
    price = 10
    ProductVersionFactory.create(
        product=ProductFactory(content_object=program), price=price
    )
    assert program.current_price == price


def test_program_page():
    """
    page property should return an associated Wagtail page if one exists
    """
    program = ProgramFactory.create()
    assert program.page is None
    page = ProgramPageFactory.create(program=program)
    assert program.page == page


def test_program_page_properties():
    """
    Wagtail-page-related properties should return expected values if the Wagtail page exists
    """
    program = ProgramFactory.create()
    assert program.description is None
    assert program.duration is None
    ProgramPageFactory.create(
        program=program,
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        duration="1 week",
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert program.display_title == "<p>page title</p>"
    assert program.subhead == "subhead"
    assert program.description == "<p>desc</p>"
    assert program.duration == "1 week"
    assert program.video_title == "<p>title</p>"
    assert program.video_url == "http://test.com/mock.mp4"
    assert program.background_image.title == "background-image"


def test_program_learning_outcomes():
    """
    ProgramPage related LearningOutcomesPage should return expected values if it exists
    """
    program = ProgramFactory.create()
    program_page = ProgramPageFactory.create(program=program)

    assert program.outcomes is None
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
    assert not LearningOutcomesPage.can_create_at(program_page)


def test_program_for_teams():
    """
    ProgramPage related ForTeamsPage should return expected values if it exists
    """
    program = ProgramFactory.create()
    program_page = ProgramPageFactory.create(program=program)

    assert program.for_teams is None
    assert ForTeamsPage.can_create_at(program_page)
    teams_page = ForTeamsPageFactory.create(
        parent=program_page,
        content="<p>content</p>",
        switch_layout=True,
        action_title="Action Title",
    )
    assert program.for_teams == teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout
    assert not ForTeamsPage.can_create_at(program_page)


def test_program_learning_techniques():
    """
    ProgramPage related subpages should return expected values if they exist
    ProgramPage related LearningTechniquesPage should return expected values if it exists
    """
    program = ProgramFactory.create()

    program_page = ProgramPageFactory.create(
        program=program, description="<p>desc</p>", duration="1 week"
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


def test_courseware_url(settings):
    """Test that the courseware_url property yields the correct values"""
    settings.OPENEDX_BASE_REDIRECT_URL = "http://example.com"
    course_run = CourseRunFactory.build(courseware_url_path="/path")
    course_run_no_path = CourseRunFactory.build(courseware_url_path=None)
    assert course_run.courseware_url == "http://example.com/path"
    assert course_run_no_path.courseware_url is None


@pytest.mark.parametrize("end_days,expected", [[-1, True], [1, False], [None, False]])
def test_course_run_past(end_days, expected):
    """
    Test that CourseRun.is_past returns the expected boolean value
    """
    now = now_in_utc()
    end_date = None if end_days is None else (now + timedelta(days=end_days))
    assert CourseRunFactory.create(end_date=end_date).is_past is expected


@pytest.mark.parametrize(
    "end_days, enroll_days, expected",
    [
        [None, None, True],
        [None, 1, True],
        [None, -1, False],
        [1, None, True],
        [-1, None, False],
        [1, -1, False],
    ],
)
def test_course_run_not_beyond_enrollment(end_days, enroll_days, expected):
    """
    Test that CourseRun.is_beyond_enrollment returns the expected boolean value
    """
    now = now_in_utc()
    end_date = None if end_days is None else now + timedelta(days=end_days)
    enr_end_date = None if enroll_days is None else now + timedelta(days=enroll_days)
    assert (
        CourseRunFactory.create(
            end_date=end_date, enrollment_end=enr_end_date
        ).is_not_beyond_enrollment
        is expected
    )


@pytest.mark.parametrize(
    "end_days,enroll_days,expected", [[-1, 1, False], [1, -1, False], [1, 1, True]]
)
def test_course_run_unexpired(end_days, enroll_days, expected):
    """
    Test that CourseRun.is_unexpired returns the expected boolean value
    """
    now = now_in_utc()
    end_date = now + timedelta(days=end_days)
    enr_end_date = now + timedelta(days=enroll_days)
    assert (
        CourseRunFactory.create(
            end_date=end_date, enrollment_end=enr_end_date
        ).is_unexpired
        is expected
    )


def test_course_first_unexpired_run():
    """
    Test that the first unexpired run of a course is returned
    """
    course = CourseFactory.create()
    now = now_in_utc()
    end_date = now + timedelta(days=100)
    enr_end_date = now + timedelta(days=100)
    first_run = CourseRunFactory.create(
        start_date=now, course=course, end_date=end_date, enrollment_end=enr_end_date
    )
    CourseRunFactory.create(
        start_date=now + timedelta(days=50),
        course=course,
        end_date=end_date,
        enrollment_end=enr_end_date,
    )
    assert course.first_unexpired_run == first_run


def test_course_next_run_date():
    """
    next_run_date should return the date of the CourseRun with the nearest future start date
    """
    course = CourseFactory.create()
    CourseRunFactory.create_batch(2, course=course, past_start=True)
    assert course.next_run_date is None

    now = now_in_utc()
    future_dates = [now + timedelta(hours=1), now + timedelta(hours=2)]
    CourseRunFactory.create_batch(
        2, course=course, start_date=factory.Iterator(future_dates)
    )
    assert course.next_run_date == future_dates[0]


def test_course_current_price():
    """
    current_price should return the price of the latest product version if it exists
    """
    course = CourseFactory.create()
    assert course.current_price is None
    price = 10
    ProductVersionFactory.create(
        product=ProductFactory(content_object=course), price=price
    )
    assert course.current_price == price


def test_course_page():
    """
    page property should return an associated Wagtail page if one exists
    """
    course = CourseFactory.create()
    assert course.page is None
    page = CoursePageFactory.create(course=course)
    assert course.page == page


def test_course_page_properties():
    """
    Wagtail-page-related properties should return expected values if the Wagtail page exists
    """
    course = CourseFactory.create()
    assert course.display_title is None
    assert course.subhead is None
    assert course.description is None
    assert course.duration is None
    assert course.video_title is None
    assert course.video_url is None
    assert course.background_image is None
    assert course.background_image_url is None
    assert course.background_image_mobile_url is None
    course_page = CoursePageFactory.create(
        course=course,
        title="<p>page title</p>",
        subhead="subhead",
        description="<p>desc</p>",
        duration="1 week",
        video_title="<p>title</p>",
        video_url="http://test.com/mock.mp4",
        background_image__title="background-image",
    )
    assert course.display_title == "<p>page title</p>"
    assert course.subhead == "subhead"
    assert course.description == "<p>desc</p>"
    assert course.duration == "1 week"
    assert course.video_title == "<p>title</p>"
    assert course.video_url == "http://test.com/mock.mp4"
    assert course.background_image.title == "background-image"


def test_course_learning_outcomes():
    """
    CoursePage related LearningOutcomesPage should return expected values if it exists
    """
    course = CourseFactory.create()
    course_page = CoursePageFactory.create(course=course)

    assert course.outcomes is None
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
    assert course.outcomes == learning_outcomes_page
    assert not LearningOutcomesPage.can_create_at(course_page)


def test_course_learning_techniques():
    """
    CoursePage related subpages should return expected values if they exist
    CoursePage related LearningTechniquesPage should return expected values if it exists
    """
    course = CourseFactory.create()

    course_page = CoursePageFactory.create(course=course)

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


def test_course_page_faq_property():
    """ Faqs property should return list of faqs related to given course."""
    course = CourseFactory.create()
    assert course.faqs is None

    course_page = CoursePageFactory.create(course=course)
    assert FrequentlyAskedQuestionPage.can_create_at(course_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=course_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is course_page
    assert list(course.faqs) == [faq]


def test_program_page_faq_property():
    """ Faqs property should return list of faqs related to given program."""
    program = ProgramFactory.create()
    assert program.faqs is None

    program_page = ProgramPageFactory.create(program=program)
    assert FrequentlyAskedQuestionPage.can_create_at(program_page)

    faqs_page = FrequentlyAskedQuestionPageFactory.create(parent=program_page)
    faq = FrequentlyAskedQuestionFactory.create(faqs_page=faqs_page)

    assert faqs_page.get_parent() is program_page
    assert list(program.faqs) == [faq]


def test_course_for_teams():
    """
    The ForTeams property should return expected values if associated with a course
    """
    course = CourseFactory.create()
    assert course.for_teams is None

    course_page = CoursePageFactory.create(course=course)
    assert ForTeamsPage.can_create_at(course_page)
    teams_page = ForTeamsPageFactory.create(
        parent=course_page,
        content="<p>content</p>",
        switch_layout=True,
        action_title="Action Title",
    )
    assert course.for_teams is teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout


def test_program_for_teams():
    """
    The ForTeams property should return expected values if associated with a program
    """
    program = CourseFactory.create()
    assert program.for_teams is None

    program_page = ProgramPageFactory.create(program=program)
    assert ForTeamsPage.can_create_at(program_page)
    teams_page = ForTeamsPageFactory.create(
        parent=program_page,
        content="<p>content</p>",
        switch_layout=True,
        action_title="Action Title",
    )
    assert program.for_teams is teams_page
    assert teams_page.action_title == "Action Title"
    assert teams_page.content == "<p>content</p>"
    assert teams_page.switch_layout
    assert not ForTeamsPage.can_create_at(course_page)

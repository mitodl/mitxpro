"""
Sync external course API tests
"""

import json
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from wagtail.test.utils.wagtail_factories import ImageFactory

from cms.factories import (
    CertificatePageFactory,
    CourseIndexPageFactory,
    ExternalCoursePageFactory,
    HomePageFactory,
)
from cms.models import CertificatePage
from courses.factories import CourseFactory, CourseRunFactory, PlatformFactory
from courses.models import Course
from courses.sync_external_courses.external_course_sync_api import (
    EMERITUS_PLATFORM_NAME,
    GLOBAL_ALUMNI_PLATFORM_NAME,
    EmeritusKeyMap,
    ExternalCourse,
    GlobalAlumniKeyMap,
    create_learning_outcomes_page,
    create_or_update_certificate_page,
    create_or_update_external_course_page,
    create_or_update_external_course_run,
    create_or_update_product_and_product_version,
    create_who_should_enroll_in_page,
    fetch_external_courses,
    generate_external_course_run_courseware_id,
    generate_external_course_run_tag,
    parse_external_course_data_str,
    save_page_revision,
    update_external_course_runs,
    deactivate_missing_course_runs,
)
from courses.management.utils import StatsCollector
from ecommerce.factories import ProductFactory, ProductVersionFactory
from mitxpro.test_utils import MockResponse
from mitxpro.utils import clean_url, now_in_utc


@pytest.fixture
def external_course_data(request):
    """
    External Course data with Future dates.
    """
    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        external_course_data = json.load(test_data_file)["rows"][0]

    params = request.param
    platform = params.get("platform", EMERITUS_PLATFORM_NAME)
    if platform == EMERITUS_PLATFORM_NAME:
        external_course_data["course_run_code"] = "MO-DBIP.ELE-99-09#1"
    elif platform == GLOBAL_ALUMNI_PLATFORM_NAME:
        external_course_data["course_run_code"] = "MXP-DBIP.ELE-99-09#1"
        external_course_data.pop("ceu", None)

    external_course_data["start_date"] = "2099-09-30"
    external_course_data["end_date"] = "2099-11-30"
    return external_course_data


@pytest.fixture
def external_expired_course_data(external_course_data):
    """
    External course JSON with expired dates.
    """
    expired_external_course_json = external_course_data.copy()
    expired_external_course_json["start_date"] = (
        datetime.now() - timedelta(days=2)  # noqa: DTZ005
    ).strftime("%Y-%m-%d")
    expired_external_course_json["end_date"] = (
        datetime.now() - timedelta(days=1)  # noqa: DTZ005
    ).strftime("%Y-%m-%d")
    return expired_external_course_json


@pytest.fixture
def external_course_with_bad_data(external_course_data):
    """
    External course JSON with bad data, i.e. program_name, course_code, course_run_code is null.
    """
    bad_data_external_course_json = external_course_data.copy()
    bad_data_external_course_json["program_name"] = None
    return bad_data_external_course_json


@pytest.fixture
def external_course_data_with_null_price(external_course_data):
    """
    External course JSON with null price.
    """
    external_course_json = external_course_data.copy()
    external_course_json["list_price"] = None
    return external_course_json


@pytest.fixture
def external_course_data_with_non_usd_price(external_course_data):
    """
    External course JSON with non USD price.
    """
    external_course_json = external_course_data.copy()
    external_course_json["list_currency"] = "INR"
    external_course_json["course_run_code"] = (
        f"{external_course_data['course_run_code'].split('-')[0]}-INRC-98-10#1"
    )
    return external_course_json


def get_keymap(run_code):
    return EmeritusKeyMap() if run_code.startswith("MO") else GlobalAlumniKeyMap()


def get_platform(run_code):
    return (
        EMERITUS_PLATFORM_NAME
        if run_code.startswith("MO")
        else GLOBAL_ALUMNI_PLATFORM_NAME
    )


@pytest.mark.parametrize(
    ("external_course_run_code", "expected_course_run_tag"),
    [
        ("MO-EOB-18-01#1", "18-01-1"),
        ("MXP-EOB-18-01#1", "18-01-1"),
        ("MO-EOB-08-01#1", "08-01-1"),
        ("MXP-EOB-08-01#1", "08-01-1"),
        ("MO-EOB-08-12#1", "08-12-1"),
        ("MXP-EOB-08-12#1", "08-12-1"),
        ("MO-EOB-18-01#12", "18-01-12"),
        ("MXP-EOB-18-01#12", "18-01-12"),
        ("MO-EOB-18-01#212", "18-01-212"),
        ("MXP-EOB-18-01#212", "18-01-212"),
    ],
)
def test_generate_external_course_run_tag(
    external_course_run_code, expected_course_run_tag
):
    """
    Tests that `generate_external_course_run_tag` generates the expected course tag for External Course Run Codes.
    """
    assert (
        generate_external_course_run_tag(external_course_run_code)
        == expected_course_run_tag
    )


@pytest.mark.parametrize(
    ("course_readable_id", "course_run_tag", "expected_course_run_courseware_id"),
    [
        ("course-v1:xPRO+EOB", "18-01#1", "course-v1:xPRO+EOB+18-01#1"),
        ("course-v1:xPRO+EOB", "08-01#1", "course-v1:xPRO+EOB+08-01#1"),
        ("course-v1:xPRO+EOB", "18-01#12", "course-v1:xPRO+EOB+18-01#12"),
        ("course-v1:xPRO+EOB", "18-01#212", "course-v1:xPRO+EOB+18-01#212"),
    ],
)
def test_generate_external_course_run_courseware_id(
    course_readable_id, course_run_tag, expected_course_run_courseware_id
):
    """
    Test that `generate_external_course_run_courseware_id` returns the expected courseware_id for the given
    course run tag and course readable id.
    """
    assert (
        generate_external_course_run_courseware_id(course_run_tag, course_readable_id)
        == expected_course_run_courseware_id
    )


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    (
        "create_course_page",
        "publish_page",
        "is_live_and_draft",
        "create_image",
        "test_image_name_without_extension",
        "has_language",
    ),
    [
        (True, False, False, True, True, True),
        (True, True, True, True, False, True),
        (True, True, False, True, False, True),
        (False, False, False, False, False, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_external_course_page(  # noqa: PLR0913, C901
    create_course_page,
    publish_page,
    is_live_and_draft,
    create_image,
    test_image_name_without_extension,
    external_course_data,
    has_language,
):
    """
    Test that `create_or_update_external_course_page` creates a new course or updates the existing.
    """
    home_page = HomePageFactory.create(title="Home Page", subhead="<p>subhead</p>")
    course_index_page = CourseIndexPageFactory.create(parent=home_page, title="Courses")
    course = CourseFactory.create(is_external=True)

    if test_image_name_without_extension:
        external_course_data["image_name"] = external_course_data["image_name"].split(
            "."
        )[0]

    if create_image:
        ImageFactory.create(title=external_course_data["image_name"])

    if create_course_page:
        external_course_page = ExternalCoursePageFactory.create(
            course=course,
            title=external_course_data["program_name"],
            external_marketing_url="",
            duration="",
            description="",
            background_image=None,
            thumbnail_image=None,
        )
        if publish_page:
            external_course_page.save_revision().publish()
            if is_live_and_draft:
                external_course_page.title = external_course_page.title + " Draft"
                external_course_page.save_revision()
        else:
            external_course_page.unpublish()

    keymap = get_keymap(external_course_data["course_run_code"])

    # Explicitly remove the language key from the dictionary to test the case where the language is not present
    if not has_language:
        external_course_data.pop("language")

    external_course_page, course_page_created, course_page_updated = (
        create_or_update_external_course_page(
            course_index_page,
            course,
            ExternalCourse(external_course_data, keymap=keymap),
            keymap=keymap,
        )
    )
    external_course_page = external_course_page.revisions.last().as_object()

    assert external_course_page.external_marketing_url == clean_url(
        external_course_data["landing_page_url"], remove_query_params=True
    )
    assert external_course_page.course == course
    assert (
        external_course_page.duration == f"{external_course_data['total_weeks']} Weeks"
    )
    assert external_course_page.min_weeks == external_course_data["total_weeks"]
    assert external_course_page.max_weeks == external_course_data["total_weeks"]
    assert external_course_page.description == external_course_data["description"]
    assert course_page_created == (not create_course_page)
    assert course_page_updated == create_course_page

    if create_course_page and not publish_page:
        assert external_course_page.has_unpublished_changes
        assert not external_course_page.live

    if is_live_and_draft:
        assert external_course_page.has_unpublished_changes
        assert external_course_page.live
        assert (
            external_course_page.title
            == external_course_data["program_name"] + " Draft"
        )
    else:
        assert external_course_page.title == external_course_data["program_name"]

    if create_image:
        assert (
            external_course_page.background_image.title
            == external_course_data["image_name"]
        )
        assert (
            external_course_page.thumbnail_image.title
            == external_course_data["image_name"]
        )

    # Check if the language is set correctly if it is present in the external course data, otherwise it should be English
    if has_language:
        assert external_course_page.language.name == external_course_data["language"]
    else:
        assert external_course_page.language.name == "English"


@pytest.mark.parametrize(
    "external_course_data", [{"platform": EMERITUS_PLATFORM_NAME}], indirect=True
)
@pytest.mark.parametrize(
    ("existing_cert_page", "publish_certificate", "is_live_and_draft"),
    [
        (True, False, False),
        (True, True, True),
        (True, True, False),
        (False, False, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_certificate_page(
    external_course_data, existing_cert_page, publish_certificate, is_live_and_draft
):
    """
    Tests that `create_or_update_certificate_page` updates the CEUs and does not change the draft or live state.
    """
    home_page = HomePageFactory.create(title="Home Page", subhead="<p>subhead</p>")
    course_index_page = CourseIndexPageFactory.create(parent=home_page, title="Courses")
    course = CourseFactory.create(is_external=True)
    external_course_page = ExternalCoursePageFactory.create(
        parent=course_index_page,
        course=course,
        title=external_course_data["program_name"],
        external_marketing_url="",
        duration="",
        description="",
    )
    if existing_cert_page:
        certificate_page = CertificatePageFactory.create(
            parent=external_course_page, CEUs=None
        )
        if publish_certificate:
            certificate_page.save_revision().publish()
            if is_live_and_draft:
                certificate_page.CEUs = Decimal("1.2")
                certificate_page.save_revision()
        else:
            certificate_page.unpublish()

    keymap = get_keymap(external_course_data["course_run_code"])
    certificate_page, is_created, is_updated = create_or_update_certificate_page(
        external_course_page,
        ExternalCourse(external_course_data, keymap=keymap),
    )
    certificate_page = certificate_page.revisions.last().as_object()
    assert certificate_page.CEUs == Decimal(str(external_course_data["ceu"]))
    assert is_created == (not existing_cert_page)
    assert is_updated == existing_cert_page

    if publish_certificate and is_live_and_draft:
        assert certificate_page.has_unpublished_changes

    if publish_certificate or is_live_and_draft:
        assert certificate_page.live


@pytest.mark.parametrize(
    "external_course_vendor_keymap", [EmeritusKeyMap, GlobalAlumniKeyMap]
)
@pytest.mark.django_db
def test_create_who_should_enroll_in_page(external_course_vendor_keymap):
    """
    Tests that `create_who_should_enroll_in_page` creates the `WhoShouldEnrollPage`.
    """
    course_page = ExternalCoursePageFactory.create()
    who_should_enroll_str = (
        "The program is ideal for:\r\n●       Early-career IT professionals, network engineers, "
        "and system administrators wanting to gain a comprehensive overview of cybersecurity and "
        "fast-track their career progression\r\n●       IT project managers and engineers keen on "
        "gaining the ability to think critically about the threat landscape, including "
        "vulnerabilities in cybersecurity, and upgrading their resume for career "
        "advancement\r\n●       Mid- or later-career professionals seeking a career change and "
        "looking to add critical cybersecurity knowledge and foundational lessons to their resume"
    )
    create_who_should_enroll_in_page(
        course_page,
        parse_external_course_data_str(who_should_enroll_str),
        keymap=external_course_vendor_keymap(),
    )
    assert parse_external_course_data_str(who_should_enroll_str) == [
        item.value.source for item in course_page.who_should_enroll.content
    ]
    assert course_page.who_should_enroll is not None


@pytest.mark.parametrize(
    "external_course_vendor_keymap", [EmeritusKeyMap, GlobalAlumniKeyMap]
)
@pytest.mark.django_db
def test_create_learning_outcomes_page(external_course_vendor_keymap):
    """
    Tests that `create_learning_outcomes_page` creates the `LearningOutcomesPage`.
    """
    course_page = ExternalCoursePageFactory.create()
    learning_outcomes_str = (
        "This program will enable you to:\r\n●       Gain an overview of cybersecurity risk "
        "management, including its foundational concepts and relevant regulations\r\n●       "
        "Explore the domains covering various aspects of cloud technology\r\n●       "
        "Learn adversary tactics and techniques that are utilized as the foundational development "
        "of specific threat models and methodologies\r\n●       Understand the guidelines for "
        "organizations to prepare themselves against cybersecurity attacks"
    )
    create_learning_outcomes_page(
        course_page,
        parse_external_course_data_str(learning_outcomes_str),
        keymap=external_course_vendor_keymap(),
    )
    assert parse_external_course_data_str(learning_outcomes_str) == [
        item.value for item in course_page.outcomes.outcome_items
    ]
    assert course_page.outcomes is not None


def test_parse_external_course_data_str():
    """
    Tests that `parse_external_course_data_str` parses who should enroll and learning outcomes strings as expected.
    """
    data_str = (
        "This program will enable you to:\r\n●       Gain an overview of cybersecurity risk "
        "management, including its foundational concepts and relevant regulations\r\n●       "
        "Explore the domains covering various aspects of cloud technology\r\n●       "
        "Learn adversary tactics and techniques that are utilized as the foundational development "
        "of specific threat models and methodologies\r\n●       Understand the guidelines for "
        "organizations to prepare themselves against cybersecurity attacks"
    )
    assert parse_external_course_data_str(data_str) == [
        "Gain an overview of cybersecurity risk management, including "
        "its foundational concepts and relevant regulations",
        "Explore the domains covering various aspects of cloud technology",
        "Learn adversary tactics and techniques that are utilized as the foundational development "
        "of specific threat models and methodologies",
        "Understand the guidelines for organizations to prepare themselves against cybersecurity attacks",
    ]


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    ("create_existing_course_run", "empty_dates", "is_live"),
    [
        (True, True, True),
        (True, False, True),
        (False, False, True),
        (True, False, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_external_course_run(
    create_existing_course_run, empty_dates, external_course_data, is_live
):
    """
    Tests that `create_or_update_external_course_run` creates or updates a course run
    """
    keymap = get_keymap(external_course_data["course_run_code"])
    external_course = ExternalCourse(external_course_data, keymap=keymap)
    course = CourseFactory.create()
    if create_existing_course_run:
        run = CourseRunFactory.create(
            course=course,
            external_course_run_id=external_course.course_run_code,
            enrollment_start=None,
            enrollment_end=None,
            expiration_date=None,
            live=is_live,
        )
        if empty_dates:
            run.start_date = None
            run.end_date = None
            run.save()

    run, run_created, run_updated = create_or_update_external_course_run(
        course, external_course
    )
    course_runs = course.courseruns.all()
    course_run_courseware_id = generate_external_course_run_courseware_id(
        external_course.course_run_tag, course.readable_id
    )

    assert len(course_runs) == 1
    assert run.course == course
    assert run_created == (not create_existing_course_run)
    assert run_updated == create_existing_course_run
    if create_existing_course_run:
        expected_data = {
            "external_course_run_id": external_course.course_run_code,
            "start_date": external_course.start_date,
            "end_date": external_course.end_date,
            "enrollment_end": external_course.enrollment_end,
            "live": True,
        }
    else:
        expected_data = {
            "title": external_course.course_title,
            "external_course_run_id": external_course.course_run_code,
            "courseware_id": course_run_courseware_id,
            "run_tag": external_course.course_run_tag,
            "start_date": external_course.start_date,
            "end_date": external_course.end_date,
            "enrollment_end": external_course.enrollment_end,
            "live": True,
        }
    for attr_name, expected_value in expected_data.items():
        assert getattr(course_runs[0], attr_name) == expected_value


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize("create_existing_data", [True, False])
@pytest.mark.django_db
def test_update_external_course_runs(  # noqa: PLR0915, PLR0913
    external_course_data,
    create_existing_data,
    external_expired_course_data,
    external_course_with_bad_data,
    external_course_data_with_null_price,
    external_course_data_with_non_usd_price,
):
    """
    Tests that `update_external_course_runs` creates new courses and updates existing.
    """
    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        external_course_runs = json.load(test_data_file)["rows"]

    platform_name = get_platform(external_course_data["course_run_code"])
    platform = PlatformFactory.create(name=platform_name)

    if create_existing_data:
        for run in random.sample(external_course_runs, len(external_course_runs) // 2):
            course = CourseFactory.create(
                title=run["program_name"],
                platform=platform,
                external_course_id=run["course_code"],
                is_external=True,
            )
            course_run = CourseRunFactory.create(
                course=course,
                external_course_run_id=run["course_run_code"],
                enrollment_start=None,
                enrollment_end=None,
                expiration_date=None,
            )

            home_page = HomePageFactory.create(
                title="Home Page", subhead="<p>subhead</p>"
            )
            CourseIndexPageFactory.create(parent=home_page, title="Courses")
            course_page = ExternalCoursePageFactory.create(
                course=course,
                title=run["program_name"],
                external_marketing_url="",
                duration="",
                description="",
            )
            CertificatePageFactory.create(
                parent=course_page, CEUs=Decimal("1.0"), partner_logo=None
            )
            product = ProductFactory.create(content_object=course_run)
            ProductVersionFactory.create(product=product, price=run["list_price"])

    external_course_runs.append(external_expired_course_data)
    external_course_runs.append(external_course_with_bad_data)
    external_course_runs.append(external_course_data_with_null_price)
    external_course_runs.append(external_course_data_with_non_usd_price)
    keymap = get_keymap(external_course_data["course_run_code"])
    stats_collector = StatsCollector()

    update_external_course_runs(
        external_course_runs, keymap=keymap, stats_collector=stats_collector
    )
    stats = stats_collector.email_stats()
    courses = Course.objects.filter(platform=platform)

    num_courses_created = 2 if create_existing_data else 4
    num_existing_courses = 2 if create_existing_data else 0
    num_course_runs_created = 3 if create_existing_data else 5
    num_course_runs_updated = 2 if create_existing_data else 0
    num_course_pages_created = 2 if create_existing_data else 4
    num_course_pages_updated = 2 if create_existing_data else 0
    num_products_created = 2 if create_existing_data else 4
    num_product_versions_created = 2 if create_existing_data else 4
    assert len(courses) == 4
    assert len(stats["course_runs_skipped"]) == 2
    assert len(stats["course_runs_expired"]) == 1
    assert len(stats["courses_created"]) == num_courses_created
    assert len(stats["existing_courses"]) == num_existing_courses
    assert len(stats["course_runs_created"]) == num_course_runs_created
    assert len(stats["course_runs_updated"]) == num_course_runs_updated
    assert len(stats["course_pages_created"]) == num_course_pages_created
    assert len(stats["course_pages_updated"]) == num_course_pages_updated
    assert len(stats["products_created"]) == num_products_created
    assert len(stats["product_versions_created"]) == num_product_versions_created
    assert len(stats["course_runs_without_prices"]) == 1

    skipped_codes = {item.code for item in stats["course_runs_skipped"]}
    expired_codes = {item.code for item in stats["course_runs_expired"]}

    for external_course_run in external_course_runs:
        if (
            external_course_run["course_run_code"] in skipped_codes
            or external_course_run["course_run_code"] in expired_codes
        ):
            continue

        course = Course.objects.filter(
            platform=platform,
            external_course_id=external_course_run["course_code"],
            is_external=True,
        ).first()
        assert course is not None
        assert (
            course.courseruns.filter(
                external_course_run_id=external_course_run["course_run_code"]
            ).count()
            == 1
        )
        assert hasattr(course, "externalcoursepage")
        assert (
            course.courseruns.filter(
                external_course_run_id=external_course_run["course_run_code"]
            )
            .first()
            .current_price
            == external_course_run["list_price"]
        )

        course_page = course.externalcoursepage
        if external_course_run["program_for"]:
            assert course_page.who_should_enroll is not None
        if external_course_run["learning_outcomes"]:
            assert course_page.outcomes is not None
        if external_course_run.get("ceu", ""):
            certificate_page = course_page.get_child_page_of_type_including_draft(
                CertificatePage
            )
            assert certificate_page
            assert certificate_page.CEUs == Decimal(str(external_course_run["ceu"]))


@pytest.mark.parametrize(
    "external_course_vendor_keymap", [EmeritusKeyMap, GlobalAlumniKeyMap]
)
def test_fetch_external_courses_success(
    settings, mocker, external_course_vendor_keymap
):
    """
    Tests that `fetch_external_courses` makes the required calls to the `Emeritus` API. Tests the success scenario.

    Here is the expected flow:
        1. Make a get request to get a list of reports.
        2. Make a post request for the `Batch` report.
        3. If the results are not ready, wait for the job to complete and make a get request to check the status.
        4. If the results are ready after the post request, return the results.
        5. If job status is 1 or 2, it is in progress. Wait for 2 seconds and make a get request for Job status.
        6. If job status is 3, the results are ready, make a get request to collect the results and return the data.
    """
    settings.EXTERNAL_COURSE_SYNC_API_BASE_URL = (
        "https://test_external_course_sync_api.io"
    )
    settings.EXTERNAL_COURSE_SYNC_API_KEY = "test_EXTERNAL_COURSE_SYNC_API_KEY"
    settings.EXTERNAL_COURSE_SYNC_API_REQUEST_TIMEOUT = 60

    mock_get = mocker.patch(
        "courses.sync_external_courses.external_course_sync_api_client.requests.get"
    )
    mock_post = mocker.patch(
        "courses.sync_external_courses.external_course_sync_api_client.requests.post"
    )

    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        external_course_runs = json.load(test_data_file)

    keymap = external_course_vendor_keymap()
    batch_query = {
        "id": 77,
        "name": keymap.report_names[0],
    }
    mock_get.side_effect = [
        MockResponse({"results": [batch_query]}),
        MockResponse({"job": {"status": 1}}),
        MockResponse({"job": {"status": 2}}),
        MockResponse({"job": {"status": 3, "query_result_id": 1}}),
        MockResponse({"query_result": {"data": external_course_runs}}),
    ]
    mock_post.side_effect = [MockResponse({"job": {"id": 1}})]

    actual_course_runs = fetch_external_courses(keymap=keymap)

    mock_get.assert_any_call(
        "https://test_external_course_sync_api.io/api/queries?api_key=test_EXTERNAL_COURSE_SYNC_API_KEY",
        timeout=60,
    )
    mock_post.assert_called_once()
    mock_get.assert_any_call(
        "https://test_external_course_sync_api.io/api/jobs/1?api_key=test_EXTERNAL_COURSE_SYNC_API_KEY",
        timeout=60,
    )
    mock_get.assert_any_call(
        "https://test_external_course_sync_api.io/api/query_results/1?api_key=test_EXTERNAL_COURSE_SYNC_API_KEY",
        timeout=60,
    )
    assert actual_course_runs == external_course_runs["rows"]


@pytest.mark.parametrize(
    "external_course_vendor_keymap", [EmeritusKeyMap, GlobalAlumniKeyMap]
)
def test_fetch_external_courses_error(
    settings, mocker, caplog, external_course_vendor_keymap
):
    """
    Tests that `fetch_external_courses` specific calls to the External Course Sync API and Fails for Job status 3 and 4.
    """
    settings.EXTERNAL_COURSE_SYNC_API_BASE_URL = (
        "https://test_external_course_sync_api.com"
    )
    settings.EXTERNAL_COURSE_SYNC_API_KEY = "test_EXTERNAL_COURSE_SYNC_API_KEY"
    mock_get = mocker.patch(
        "courses.sync_external_courses.external_course_sync_api_client.requests.get"
    )
    mock_post = mocker.patch(
        "courses.sync_external_courses.external_course_sync_api_client.requests.post"
    )

    keymap = external_course_vendor_keymap()
    batch_query = {
        "id": 77,
        "name": keymap.report_names[0],
    }
    mock_get.side_effect = [
        MockResponse({"results": [batch_query]}),
        MockResponse({"job": {"status": 1}}),
        MockResponse({"job": {"status": 2}}),
        MockResponse({"job": {"status": 4}}),
    ]
    mock_post.side_effect = [MockResponse({"job": {"id": 1}})]
    with caplog.at_level(logging.ERROR):
        fetch_external_courses(keymap=keymap)
    assert "Job failed!" in caplog.text
    assert "Something unexpected happened!" in caplog.text


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    (
        "create_existing_product",
        "existing_price",
        "new_price",
        "expected_price",
        "expected_product_created",
        "expected_product_version_created",
        "existing_product_is_active",
    ),
    [
        (True, None, float(100), float(100), False, True, True),
        (False, None, float(100), float(100), True, True, True),
        (True, float(100), float(100), float(100), False, False, True),
        (True, float(100), float(111), float(111), False, True, True),
        (True, float(100), float(100), float(100), False, True, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_product_and_product_version(  # noqa: PLR0913
    external_course_data,
    create_existing_product,
    existing_price,
    new_price,
    expected_price,
    expected_product_created,
    expected_product_version_created,
    existing_product_is_active,
):
    """
    Tests that `create_or_update_product_and_product_version` creates or updates products and versions as required.
    """
    external_course_data["list_price"] = new_price

    keymap = get_keymap(external_course_data["course_run_code"])
    platform_name = get_platform(external_course_data["course_run_code"])
    external_course = ExternalCourse(external_course_data, keymap=keymap)
    platform = PlatformFactory.create(name=platform_name)
    course = CourseFactory.create(
        external_course_id=external_course.course_code,
        platform=platform,
        is_external=True,
        title=external_course.course_title,
        readable_id=external_course.course_readable_id,
        live=True,
    )
    course_run, _, _ = create_or_update_external_course_run(course, external_course)

    if create_existing_product:
        product = ProductFactory.create(
            content_object=course_run, is_active=existing_product_is_active
        )

        if existing_price:
            ProductVersionFactory.create(product=product, price=existing_price)

    product_created, version_created = create_or_update_product_and_product_version(
        external_course, course_run
    )
    assert course_run.current_price == expected_price
    assert product_created == expected_product_created
    assert version_created == expected_product_version_created
    assert course_run.products.first().latest_version.description
    assert course_run.products.first().latest_version.text_id
    assert course_run.products.first().is_active


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("is_draft_page", "has_unpublished_changes"),
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
)
def test_save_page_revision(is_draft_page, has_unpublished_changes):
    """
    Tests that `save_page_revision` saves a revision and publishes the page if needed.
    """
    external_course_page = ExternalCoursePageFactory.create()
    revision = external_course_page.save_revision()
    if is_draft_page:
        external_course_page.unpublish()
    else:
        revision.publish()

    if has_unpublished_changes:
        external_course_page.external_marketing_url = ""
        external_course_page.save_revision()

    latest_revision = external_course_page.get_latest_revision_as_object()
    latest_revision.external_marketing_url = "https://test-external-course-sync-api.io/Internet-of-things-iot-design-and-applications"
    save_page_revision(external_course_page, latest_revision)

    assert external_course_page.live == (not is_draft_page)

    if has_unpublished_changes:
        assert external_course_page.has_unpublished_changes


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    ("title", "course_code", "course_run_code", "is_valid", "msg"),
    [
        (
            "Internet of Things (IoT): Design and Applications     ",
            "MO-DBIP",
            "MO-DBIP.ELE-99-07#1",
            True,
            None,
        ),
        (
            "Internet of Things (IoT): Design and Applications     ",
            "MXP-DBIP",
            "MXP-DBIP.ELE-99-07#1",
            True,
            None,
        ),
        (
            "",
            "MO-DBIP",
            "MO-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_title",
        ),
        (
            "",
            "MXP-DBIP",
            "MXP-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_title",
        ),
        (
            None,
            "MO-DBIP",
            "MO-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_title",
        ),
        (
            None,
            "MXP-DBIP",
            "MXP-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_title",
        ),
        (
            "    Internet of Things (IoT): Design and Applications   ",
            "",
            "MO-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_code",
        ),
        (
            "    Internet of Things (IoT): Design and Applications   ",
            "",
            "MXP-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_code",
        ),
        (
            "    Internet of Things (IoT): Design and Applications",
            None,
            "MO-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_code",
        ),
        (
            "    Internet of Things (IoT): Design and Applications",
            None,
            "MXP-DBIP.ELE-99-07#1",
            False,
            "Missing required field course_code",
        ),
        (
            "Internet of Things (IoT): Design and Applications",
            "MO-DBIP",
            "",
            False,
            "Missing required field course_run_code",
        ),
        (
            "Internet of Things (IoT): Design and Applications",
            "MXP-DBIP",
            "",
            False,
            "Missing required field course_run_code",
        ),
        (
            "Internet of Things (IoT): Design and Applications",
            "MO-DBIP",
            None,
            False,
            "Missing required field course_run_code",
        ),
        (
            "Internet of Things (IoT): Design and Applications",
            "MXP-DBIP",
            None,
            False,
            "Missing required field course_run_code",
        ),
        (
            "",
            "",
            "",
            False,
            "Missing required field course_title",
        ),
        (
            None,
            None,
            None,
            False,
            "Missing required field course_title",
        ),
    ],
)
def test_external_course_validate_required_fields(
    external_course_data, title, course_code, course_run_code, is_valid, msg
):
    """
    Tests that ExternalCourse.validate_required_fields validates required fields.
    """
    keymap = get_keymap(external_course_data["course_run_code"])
    external_course = ExternalCourse(external_course_data, keymap=keymap)
    external_course.course_title = title.strip() if title else title
    external_course.course_code = course_code
    external_course.course_run_code = course_run_code
    valid_required_fields, required_fields_msg = (
        external_course.validate_required_fields(keymap=keymap)
    )
    assert valid_required_fields == is_valid
    assert required_fields_msg == msg


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    ("list_currency", "is_valid", "msg"),
    [
        ("USD", True, None),
        ("INR", False, "Invalid currency: INR."),
        ("EUR", False, "Invalid currency: EUR."),
        ("GBP", False, "Invalid currency: GBP."),
        ("PKR", False, "Invalid currency: PKR."),
    ],
)
def test_external_course_validate_list_currency(
    external_course_data, list_currency, is_valid, msg
):
    """
    Tests that the `USD` is the only valid currency for the External courses.
    """
    keymap = get_keymap(external_course_data["course_run_code"])
    external_course = ExternalCourse(external_course_data, keymap=keymap)
    external_course.list_currency = list_currency
    valid_currency, currency_msg = external_course.validate_list_currency()
    assert valid_currency == is_valid
    assert currency_msg == msg


@pytest.mark.parametrize(
    "external_course_data",
    [{"platform": EMERITUS_PLATFORM_NAME}, {"platform": GLOBAL_ALUMNI_PLATFORM_NAME}],
    indirect=True,
)
@pytest.mark.parametrize(
    ("end_date", "is_valid"),
    [
        (now_in_utc() + timedelta(days=1), True),
        (now_in_utc() - timedelta(days=1), False),
    ],
)
def test_external_course_validate_end_date(external_course_data, end_date, is_valid):
    """
    Tests that the valid end date is in the future for External courses.
    """
    keymap = get_keymap(external_course_data["course_run_code"])
    external_course = ExternalCourse(external_course_data, keymap=keymap)
    external_course.end_date = end_date
    assert external_course.validate_end_date() == is_valid


@pytest.mark.parametrize(
    (
        "external_course_run_id",
        "api_course_run_codes",
        "is_unexpired",
        "expected_is_live",
    ),
    [
        (
            "MO-DBIP.ELE-99-09#1",
            ["MO-DBIP.ELE-99-09#1"],
            True,
            True,
        ),
        (
            "MO-DBIP.ELE-99-09#1",
            ["MO-DBIP.ELE-99-09#2"],
            True,
            False,
        ),
        (
            "MO-DBIP.ELE-99-09#1",
            ["MO-DBIP.ELE-99-09#2"],
            False,
            True,
        ),
    ],
)
@pytest.mark.django_db
def test_deactivate_missing_course_runs(
    mocker,
    external_course_run_id,
    api_course_run_codes,
    is_unexpired,
    expected_is_live,
):
    """
    Tests that `deactivate_missing_course_runs` deactivates the missing API course runs.
    """
    platform = PlatformFactory.create(name=EMERITUS_PLATFORM_NAME)
    course = CourseFactory.create(platform=platform, is_external=True)
    course_run = CourseRunFactory.create(
        course=course,
        live=True,
        external_course_run_id=external_course_run_id,
    )
    product = ProductFactory.create(content_object=course_run)
    mocker.patch.object(
        course_run.__class__,
        "is_unexpired",
        new_callable=mocker.PropertyMock,
        return_value=is_unexpired,
    )
    mock_now = now_in_utc()
    mocker.patch(
        "courses.sync_external_courses.external_course_sync_api.now_in_utc",
        return_value=mock_now,
    )
    deactivated_runs_list = deactivate_missing_course_runs(
        api_course_run_codes, platform
    )
    course_run.refresh_from_db()
    product.refresh_from_db()
    assert (external_course_run_id in deactivated_runs_list) == (not expected_is_live)
    assert course_run.live == expected_is_live
    assert product.is_active == expected_is_live
    assert (course_run.updated_on == mock_now) == (not expected_is_live)
    assert (product.updated_on == mock_now) == (not expected_is_live)

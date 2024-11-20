"""
Sync external course API tests
"""

import json
import logging
import random
from datetime import datetime, timedelta
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
from courses.sync_external_courses.emeritus_api import (
    EmeritusCourse,
    EmeritusKeyMap,
    create_learning_outcomes_page,
    create_or_update_certificate_page,
    create_or_update_emeritus_course_page,
    create_or_update_emeritus_course_run,
    create_or_update_product_and_product_version,
    create_who_should_enroll_in_page,
    fetch_emeritus_courses,
    generate_emeritus_course_run_tag,
    generate_external_course_run_courseware_id,
    parse_emeritus_data_str,
    save_page_revision,
    update_emeritus_course_runs,
)
from ecommerce.factories import ProductFactory, ProductVersionFactory
from mitxpro.test_utils import MockResponse
from mitxpro.utils import clean_url, now_in_utc


@pytest.fixture
def emeritus_course_data():
    """
    Emeritus Course data with Future dates.
    """
    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        emeritus_course_data = json.load(test_data_file)["rows"][0]

    emeritus_course_data["start_date"] = "2099-09-30"
    emeritus_course_data["end_date"] = "2099-11-30"
    emeritus_course_data["course_run_code"] = "MO-DBIP.ELE-99-09#1"
    return emeritus_course_data


@pytest.fixture
def emeritus_expired_course_data(emeritus_course_data):
    """
    Emeritus course JSON with expired dates.
    """
    expired_emeritus_course_json = emeritus_course_data.copy()
    expired_emeritus_course_json["start_date"] = (
        datetime.now() - timedelta(days=2)  # noqa: DTZ005
    ).strftime("%Y-%m-%d")
    expired_emeritus_course_json["end_date"] = (
        datetime.now() - timedelta(days=1)  # noqa: DTZ005
    ).strftime("%Y-%m-%d")
    return expired_emeritus_course_json


@pytest.fixture
def emeritus_course_with_bad_data(emeritus_course_data):
    """
    Emeritus course JSON with bad data, i.e. program_name, course_code, course_run_code is null.
    """
    bad_data_emeritus_course_json = emeritus_course_data.copy()
    bad_data_emeritus_course_json["program_name"] = None
    return bad_data_emeritus_course_json


@pytest.fixture
def emeritus_course_data_with_null_price(emeritus_course_data):
    """
    Emeritus course JSON with null price.
    """
    emeritus_course_json = emeritus_course_data.copy()
    emeritus_course_json["list_price"] = None
    return emeritus_course_json


@pytest.fixture
def emeritus_course_data_with_non_usd_price(emeritus_course_data):
    """
    Emeritus course JSON with non USD price.
    """
    emeritus_course_json = emeritus_course_data.copy()
    emeritus_course_json["list_currency"] = "INR"
    emeritus_course_json["course_run_code"] = "MO-INRC-98-10#1"
    return emeritus_course_json


@pytest.mark.parametrize(
    ("emeritus_course_run_code", "expected_course_run_tag"),
    [
        ("MO-EOB-18-01#1", "18-01-1"),
        ("MO-EOB-08-01#1", "08-01-1"),
        ("MO-EOB-08-12#1", "08-12-1"),
        ("MO-EOB-18-01#12", "18-01-12"),
        ("MO-EOB-18-01#212", "18-01-212"),
    ],
)
def test_generate_emeritus_course_run_tag(
    emeritus_course_run_code, expected_course_run_tag
):
    """
    Tests that `generate_emeritus_course_run_tag` generates the expected course tag for Emeritus Course Run Codes.
    """
    assert (
        generate_emeritus_course_run_tag(emeritus_course_run_code)
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
    (
        "create_course_page",
        "publish_page",
        "is_live_and_draft",
        "create_image",
        "test_image_name_without_extension",
    ),
    [
        (True, False, False, True, True),
        (True, True, True, True, False),
        (True, True, False, True, False),
        (False, False, False, False, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_emeritus_course_page(  # noqa: PLR0913
    create_course_page,
    publish_page,
    is_live_and_draft,
    create_image,
    test_image_name_without_extension,
    emeritus_course_data,
):
    """
    Test that `create_or_update_emeritus_course_page` creates a new course or updates the existing.
    """
    home_page = HomePageFactory.create(title="Home Page", subhead="<p>subhead</p>")
    course_index_page = CourseIndexPageFactory.create(parent=home_page, title="Courses")
    course = CourseFactory.create(is_external=True)

    if test_image_name_without_extension:
        emeritus_course_data["image_name"] = emeritus_course_data["image_name"].split(
            "."
        )[0]

    if create_image:
        ImageFactory.create(title=emeritus_course_data["image_name"])

    if create_course_page:
        external_course_page = ExternalCoursePageFactory.create(
            course=course,
            title=emeritus_course_data["program_name"],
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

    external_course_page, course_page_created, course_page_updated = (
        create_or_update_emeritus_course_page(
            course_index_page, course, EmeritusCourse(emeritus_course_data)
        )
    )
    external_course_page = external_course_page.revisions.last().as_object()

    assert external_course_page.external_marketing_url == clean_url(
        emeritus_course_data["landing_page_url"], remove_query_params=True
    )
    assert external_course_page.course == course
    assert (
        external_course_page.duration == f"{emeritus_course_data['total_weeks']} Weeks"
    )
    assert external_course_page.description == emeritus_course_data["description"]
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
            == emeritus_course_data["program_name"] + " Draft"
        )
    else:
        assert external_course_page.title == emeritus_course_data["program_name"]

    if create_image:
        assert (
            external_course_page.background_image.title
            == emeritus_course_data["image_name"]
        )
        assert (
            external_course_page.thumbnail_image.title
            == emeritus_course_data["image_name"]
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
    emeritus_course_data, existing_cert_page, publish_certificate, is_live_and_draft
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
        title=emeritus_course_data["program_name"],
        external_marketing_url="",
        duration="",
        description="",
    )
    if existing_cert_page:
        certificate_page = CertificatePageFactory.create(
            parent=external_course_page, CEUs=""
        )
        if publish_certificate:
            certificate_page.save_revision().publish()
            if is_live_and_draft:
                certificate_page.CEUs = "1.2"
                certificate_page.save_revision()
        else:
            certificate_page.unpublish()

    certificate_page, is_created, is_updated = create_or_update_certificate_page(
        external_course_page, EmeritusCourse(emeritus_course_data)
    )
    certificate_page = certificate_page.revisions.last().as_object()
    assert certificate_page.CEUs == emeritus_course_data["ceu"]
    assert is_created == (not existing_cert_page)
    assert is_updated == existing_cert_page

    if publish_certificate and is_live_and_draft:
        assert certificate_page.has_unpublished_changes

    if publish_certificate or is_live_and_draft:
        assert certificate_page.live


@pytest.mark.django_db
def test_create_who_should_enroll_in_page():
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
        course_page, parse_emeritus_data_str(who_should_enroll_str)
    )
    assert parse_emeritus_data_str(who_should_enroll_str) == [
        item.value.source for item in course_page.who_should_enroll.content
    ]
    assert course_page.who_should_enroll is not None


@pytest.mark.django_db
def test_create_learning_outcomes_page():
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
        course_page, parse_emeritus_data_str(learning_outcomes_str)
    )
    assert parse_emeritus_data_str(learning_outcomes_str) == [
        item.value for item in course_page.outcomes.outcome_items
    ]
    assert course_page.outcomes is not None


def test_parse_emeritus_data_str():
    """
    Tests that `parse_emeritus_data_str` parses who should enroll and learning outcomes strings as expected.
    """
    data_str = (
        "This program will enable you to:\r\n●       Gain an overview of cybersecurity risk "
        "management, including its foundational concepts and relevant regulations\r\n●       "
        "Explore the domains covering various aspects of cloud technology\r\n●       "
        "Learn adversary tactics and techniques that are utilized as the foundational development "
        "of specific threat models and methodologies\r\n●       Understand the guidelines for "
        "organizations to prepare themselves against cybersecurity attacks"
    )
    assert parse_emeritus_data_str(data_str) == [
        "Gain an overview of cybersecurity risk management, including "
        "its foundational concepts and relevant regulations",
        "Explore the domains covering various aspects of cloud technology",
        "Learn adversary tactics and techniques that are utilized as the foundational development "
        "of specific threat models and methodologies",
        "Understand the guidelines for organizations to prepare themselves against cybersecurity attacks",
    ]


@pytest.mark.parametrize(
    ("create_existing_course_run", "empty_dates"),
    [
        (True, True),
        (True, False),
        (False, False),
    ],
)
@pytest.mark.django_db
def test_create_or_update_emeritus_course_run(
    create_existing_course_run, empty_dates, emeritus_course_data
):
    """
    Tests that `create_or_update_emeritus_course_run` creates or updates a course run
    """
    emeritus_course = EmeritusCourse(emeritus_course_data)
    course = CourseFactory.create()
    if create_existing_course_run:
        run = CourseRunFactory.create(
            course=course,
            external_course_run_id=emeritus_course.course_run_code,
            enrollment_start=None,
            enrollment_end=None,
            expiration_date=None,
        )
        if empty_dates:
            run.start_date = None
            run.end_date = None
            run.save()

    run, run_created, run_updated = create_or_update_emeritus_course_run(
        course, emeritus_course
    )
    course_runs = course.courseruns.all()
    course_run_courseware_id = generate_external_course_run_courseware_id(
        emeritus_course.course_run_tag, course.readable_id
    )

    assert len(course_runs) == 1
    assert run.course == course
    assert run_created == (not create_existing_course_run)
    assert run_updated == create_existing_course_run
    if create_existing_course_run:
        expected_data = {
            "external_course_run_id": emeritus_course.course_run_code,
            "start_date": emeritus_course.start_date,
            "end_date": emeritus_course.end_date,
            "enrollment_end": emeritus_course.enrollment_end,
        }
    else:
        expected_data = {
            "title": emeritus_course.course_title,
            "external_course_run_id": emeritus_course.course_run_code,
            "courseware_id": course_run_courseware_id,
            "run_tag": emeritus_course.course_run_tag,
            "start_date": emeritus_course.start_date,
            "end_date": emeritus_course.end_date,
            "enrollment_end": emeritus_course.enrollment_end,
            "live": True,
        }
    for attr_name, expected_value in expected_data.items():
        assert getattr(course_runs[0], attr_name) == expected_value


@pytest.mark.parametrize("create_existing_data", [True, False])
@pytest.mark.django_db
def test_update_emeritus_course_runs(  # noqa: PLR0915
    create_existing_data,
    emeritus_expired_course_data,
    emeritus_course_with_bad_data,
    emeritus_course_data_with_null_price,
    emeritus_course_data_with_non_usd_price,
):
    """
    Tests that `update_emeritus_course_runs` creates new courses and updates existing.
    """
    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        emeritus_course_runs = json.load(test_data_file)["rows"]

    platform = PlatformFactory.create(name=EmeritusKeyMap.PLATFORM_NAME.value)

    if create_existing_data:
        for run in random.sample(emeritus_course_runs, len(emeritus_course_runs) // 2):
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
                parent=course_page, CEUs="1.0", partner_logo=None
            )
            product = ProductFactory.create(content_object=course_run)
            ProductVersionFactory.create(product=product, price=run["list_price"])

    emeritus_course_runs.append(emeritus_expired_course_data)
    emeritus_course_runs.append(emeritus_course_with_bad_data)
    emeritus_course_runs.append(emeritus_course_data_with_null_price)
    emeritus_course_runs.append(emeritus_course_data_with_non_usd_price)
    stats = update_emeritus_course_runs(emeritus_course_runs)
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

    for emeritus_course_run in emeritus_course_runs:
        if (
            emeritus_course_run["course_run_code"] in stats["course_runs_skipped"]
            or emeritus_course_run["course_run_code"] in stats["course_runs_expired"]
        ):
            continue

        course = Course.objects.filter(
            platform=platform,
            external_course_id=emeritus_course_run["course_code"],
            is_external=True,
        ).first()
        assert course is not None
        assert (
            course.courseruns.filter(
                external_course_run_id=emeritus_course_run["course_run_code"]
            ).count()
            == 1
        )
        assert hasattr(course, "externalcoursepage")
        assert (
            course.courseruns.filter(
                external_course_run_id=emeritus_course_run["course_run_code"]
            )
            .first()
            .current_price
            == emeritus_course_run["list_price"]
        )

        course_page = course.externalcoursepage
        if emeritus_course_run["program_for"]:
            assert course_page.who_should_enroll is not None
        if emeritus_course_run["learning_outcomes"]:
            assert course_page.outcomes is not None
        if emeritus_course_run.get("ceu", ""):
            certificate_page = course_page.get_child_page_of_type_including_draft(
                CertificatePage
            )
            assert certificate_page
            assert certificate_page.CEUs == emeritus_course_run["ceu"]


def test_fetch_emeritus_courses_success(settings, mocker):
    """
    Tests that `fetch_emeritus_courses` makes the required calls to the `Emeritus` API. Tests the success scenario.

    Here is the expected flow:
        1. Make a get request to get a list of reports.
        2. Make a post request for the `Batch` report.
        3. If the results are not ready, wait for the job to complete and make a get request to check the status.
        4. If the results are ready after the post request, return the results.
        5. If job status is 1 or 2, it is in progress. Wait for 2 seconds and make a get request for Job status.
        6. If job status is 3, the results are ready, make a get request to collect the results and return the data.
    """
    settings.EMERITUS_API_BASE_URL = "https://test_emeritus_api.io"
    settings.EMERITUS_API_KEY = "test_emeritus_api_key"
    settings.EMERITUS_API_REQUEST_TIMEOUT = 60

    mock_get = mocker.patch(
        "courses.sync_external_courses.emeritus_api_client.requests.get"
    )
    mock_post = mocker.patch(
        "courses.sync_external_courses.emeritus_api_client.requests.post"
    )

    with Path(
        "courses/sync_external_courses/test_data/batch_test.json"
    ).open() as test_data_file:
        emeritus_course_runs = json.load(test_data_file)

    batch_query = {
        "id": 77,
        "name": "Batch",
    }
    mock_get.side_effect = [
        MockResponse({"results": [batch_query]}),
        MockResponse({"job": {"status": 1}}),
        MockResponse({"job": {"status": 2}}),
        MockResponse({"job": {"status": 3, "query_result_id": 1}}),
        MockResponse({"query_result": {"data": emeritus_course_runs}}),
    ]
    mock_post.side_effect = [MockResponse({"job": {"id": 1}})]

    actual_course_runs = fetch_emeritus_courses()

    mock_get.assert_any_call(
        "https://test_emeritus_api.io/api/queries?api_key=test_emeritus_api_key",
        timeout=60,
    )
    mock_post.assert_called_once()
    mock_get.assert_any_call(
        "https://test_emeritus_api.io/api/jobs/1?api_key=test_emeritus_api_key",
        timeout=60,
    )
    mock_get.assert_any_call(
        "https://test_emeritus_api.io/api/query_results/1?api_key=test_emeritus_api_key",
        timeout=60,
    )
    assert actual_course_runs == emeritus_course_runs["rows"]


def test_fetch_emeritus_courses_error(settings, mocker, caplog):
    """
    Tests that `fetch_emeritus_courses` specific calls to the Emeritus API and Fails for Job status 3 and 4.
    """
    settings.EMERITUS_API_BASE_URL = "https://test_emeritus_api.com"
    settings.EMERITUS_API_KEY = "test_emeritus_api_key"
    mock_get = mocker.patch(
        "courses.sync_external_courses.emeritus_api_client.requests.get"
    )
    mock_post = mocker.patch(
        "courses.sync_external_courses.emeritus_api_client.requests.post"
    )

    batch_query = {
        "id": 77,
        "name": "Batch",
    }
    mock_get.side_effect = [
        MockResponse({"results": [batch_query]}),
        MockResponse({"job": {"status": 1}}),
        MockResponse({"job": {"status": 2}}),
        MockResponse({"job": {"status": 4}}),
    ]
    mock_post.side_effect = [MockResponse({"job": {"id": 1}})]
    with caplog.at_level(logging.ERROR):
        fetch_emeritus_courses()
    assert "Job failed!" in caplog.text
    assert "Something unexpected happened!" in caplog.text


@pytest.mark.parametrize(
    (
        "create_existing_product",
        "existing_price",
        "new_price",
        "expected_price",
        "expected_product_created",
        "expected_product_version_created",
    ),
    [
        (True, None, float(100), float(100), False, True),
        (False, None, float(100), float(100), True, True),
        (True, float(100), float(100), float(100), False, False),
        (True, float(100), float(111), float(111), False, True),
    ],
)
@pytest.mark.django_db
def test_create_or_update_product_and_product_version(  # noqa: PLR0913
    emeritus_course_data,
    create_existing_product,
    existing_price,
    new_price,
    expected_price,
    expected_product_created,
    expected_product_version_created,
):
    """
    Tests that `create_or_update_product_and_product_version` creates or updates products and versions as required.
    """
    emeritus_course_data["list_price"] = new_price
    emeritus_course = EmeritusCourse(emeritus_course_data)
    platform = PlatformFactory.create(name=EmeritusKeyMap.PLATFORM_NAME)
    course = CourseFactory.create(
        external_course_id=emeritus_course.course_code,
        platform=platform,
        is_external=True,
        title=emeritus_course.course_title,
        readable_id=emeritus_course.course_readable_id,
        live=True,
    )
    course_run, _, _ = create_or_update_emeritus_course_run(course, emeritus_course)

    if create_existing_product:
        product = ProductFactory.create(content_object=course_run)

        if existing_price:
            ProductVersionFactory.create(product=product, price=existing_price)

    product_created, version_created = create_or_update_product_and_product_version(
        emeritus_course, course_run
    )
    assert course_run.current_price == expected_price
    assert product_created == expected_product_created
    assert version_created == expected_product_version_created
    assert course_run.products.first().latest_version.description
    assert course_run.products.first().latest_version.text_id


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
    latest_revision.external_marketing_url = (
        "https://test-emeritus-api.io/Internet-of-things-iot-design-and-applications"
    )
    save_page_revision(external_course_page, latest_revision)

    assert external_course_page.live == (not is_draft_page)

    if has_unpublished_changes:
        assert external_course_page.has_unpublished_changes


@pytest.mark.parametrize(
    ("title", "course_code", "course_run_code", "is_valid"),
    [
        (
            "Internet of Things (IoT): Design and Applications     ",
            "MO-DBIP",
            "MO-DBIP.ELE-99-07#1",
            True,
        ),
        ("", "MO-DBIP", "MO-DBIP.ELE-99-07#1", False),
        (None, "MO-DBIP", "MO-DBIP.ELE-99-07#1", False),
        (
            "    Internet of Things (IoT): Design and Applications   ",
            "",
            "MO-DBIP.ELE-99-07#1",
            False,
        ),
        (
            "    Internet of Things (IoT): Design and Applications",
            None,
            "MO-DBIP.ELE-99-07#1",
            False,
        ),
        ("Internet of Things (IoT): Design and Applications", "MO-DBIP", "", False),
        ("Internet of Things (IoT): Design and Applications", "MO-DBIP", None, False),
        ("", "", "", False),
        (None, None, None, False),
    ],
)
def test_emeritus_course_validate_required_fields(
    emeritus_course_data, title, course_code, course_run_code, is_valid
):
    """
    Tests that EmeritusCourse.validate_required_fields validates required fields.
    """
    emeritus_course = EmeritusCourse(emeritus_course_data)
    emeritus_course.course_title = title.strip() if title else title
    emeritus_course.course_code = course_code
    emeritus_course.course_run_code = course_run_code
    assert emeritus_course.validate_required_fields() == is_valid


@pytest.mark.parametrize(
    ("list_currency", "is_valid"),
    [
        ("USD", True),
        ("INR", False),
        ("EUR", False),
        ("GBP", False),
        ("PKR", False),
    ],
)
def test_emeritus_course_validate_list_currency(
    emeritus_course_data, list_currency, is_valid
):
    """
    Tests that the `USD` is the only valid currency for the Emeritus courses.
    """
    emeritus_course = EmeritusCourse(emeritus_course_data)
    emeritus_course.list_currency = list_currency
    assert emeritus_course.validate_list_currency() == is_valid


@pytest.mark.parametrize(
    ("end_date", "is_valid"),
    [
        (now_in_utc() + timedelta(days=1), True),
        (now_in_utc() - timedelta(days=1), False),
    ],
)
def test_emeritus_course_validate_end_date(emeritus_course_data, end_date, is_valid):
    """
    Tests that the valid end date is in the future for Emeritus courses.
    """
    emeritus_course = EmeritusCourse(emeritus_course_data)
    emeritus_course.end_date = end_date
    assert emeritus_course.validate_end_date() == is_valid

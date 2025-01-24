"""
Tests for course views
"""

import json
import operator as op
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from mitol.digitalcredentials.models import DigitalCredentialRequest
from mitol.digitalcredentials.serializers import DigitalCredentialRequestSerializer
from rest_framework import status

from cms.factories import (
    CoursePageFactory,
    ExternalCoursePageFactory,
    ProgramPageFactory,
)
from courses.api import UserEnrollments
from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    CourseTopicFactory,
    ProgramCertificateFactory,
    ProgramEnrollmentFactory,
    ProgramFactory,
)
from courses.serializers import (
    CourseRunCertificateSerializer,
    CourseRunSerializer,
    CourseSerializer,
    ProgramCertificateSerializer,
    ProgramSerializer,
)
from courses.sync_external_courses.external_course_sync_api import (
    EMERITUS_PLATFORM_NAME,
    GLOBAL_ALUMNI_PLATFORM_NAME,
)
from ecommerce.factories import ProductFactory, ProductVersionFactory
from mitxpro.test_utils import assert_drf_json_equal
from mitxpro.utils import now_in_utc

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def programs():
    """Fixture for a set of Programs in the database"""
    programs = ProgramFactory.create_batch(3)
    for program in programs:
        ProductVersionFactory.create(product=ProductFactory(content_object=program))
    return programs


@pytest.fixture
def courses():
    """Fixture for a set of Courses in the database"""
    return CourseFactory.create_batch(3)


@pytest.fixture
def course_runs():
    """Fixture for a set of CourseRuns in the database"""
    return CourseRunFactory.create_batch(3)


def test_get_programs(user_drf_client, programs):
    """Test the view that handles requests for all Programs"""
    ProgramPageFactory.create_batch(
        2, live=False
    )  # create live programs with draft pages
    ProgramFactory.create(live=False)  # draft program
    ProgramFactory.create(page=None)  # live program, no CMS page
    resp = user_drf_client.get(reverse("programs_api-list"))
    programs_data = sorted(resp.json(), key=op.itemgetter("id"))
    assert len(programs_data) == len(programs)
    for program, program_data in zip(programs, programs_data):
        assert_drf_json_equal(program_data, ProgramSerializer(program).data)


def test_get_program(user_drf_client, programs):
    """Test the view that handles a request for single Program"""
    program = programs[0]
    resp = user_drf_client.get(
        reverse("programs_api-detail", kwargs={"pk": program.id})
    )
    program_data = resp.json()
    assert_drf_json_equal(program_data, ProgramSerializer(program).data)


def test_create_program(user_drf_client, programs):
    """Test the view that handles a request to create a Program"""
    program = programs[0]
    program_data = ProgramSerializer(program).data
    del program_data["id"]
    program_data["title"] = "New Program Title"
    request_url = reverse("programs_api-list")
    resp = user_drf_client.post(request_url, program_data)
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_patch_program(user_drf_client, programs):
    """Test the view that handles a request to patch a Program"""
    program = programs[0]
    request_url = reverse("programs_api-detail", kwargs={"pk": program.id})
    resp = user_drf_client.patch(request_url, {"title": "New Program Title"})
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_delete_program(user_drf_client, programs):
    """Test the view that handles a request to delete a Program"""
    program = programs[0]
    resp = user_drf_client.delete(
        reverse("programs_api-detail", kwargs={"pk": program.id})
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.parametrize("is_anonymous", [True, False])
def test_get_courses(user_drf_client, courses, mock_context, is_anonymous):
    """Test the view that handles requests for all Courses"""
    CoursePageFactory.create_batch(
        2, live=False
    )  # create live courses with draft pages
    CourseFactory.create(page=None)  # live course with no cms page
    CourseFactory.create(live=False)  # Draft course
    if is_anonymous:
        user_drf_client.logout()
    resp = user_drf_client.get(reverse("courses_api-list"))
    courses_data = resp.json()
    assert len(courses_data) == len(courses)
    for course, course_data in zip(courses, courses_data):
        course_data["credits"] = (
            Decimal(str(course_data["credits"])) if course_data["credits"] else None
        )
        assert (
            course_data == CourseSerializer(instance=course, context=mock_context).data
        )


@pytest.mark.parametrize("is_anonymous", [True, False])
def test_get_course(user_drf_client, courses, mock_context, is_anonymous):
    """Test the view that handles a request for single Course"""
    if is_anonymous:
        user_drf_client.logout()
    course = courses[0]
    resp = user_drf_client.get(reverse("courses_api-detail", kwargs={"pk": course.id}))
    course_data = resp.json()
    course_data["credits"] = (
        Decimal(str(course_data["credits"])) if course_data["credits"] else None
    )
    assert course_data == CourseSerializer(instance=course, context=mock_context).data


def test_create_course(user_drf_client, courses, mock_context):
    """Test the view that handles a request to create a Course"""
    course = courses[0]
    course_data = CourseSerializer(instance=course, context=mock_context).data
    del course_data["id"]
    course_data["title"] = "New Course Title"
    request_url = reverse("courses_api-list")
    resp = user_drf_client.post(request_url, course_data)
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_patch_course(user_drf_client, courses):
    """Test the view that handles a request to patch a Course"""
    course = courses[0]
    request_url = reverse("courses_api-detail", kwargs={"pk": course.id})
    resp = user_drf_client.patch(request_url, {"title": "New Course Title"})
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_delete_course(user_drf_client, courses):
    """Test the view that handles a request to delete a Course"""
    course = courses[0]
    resp = user_drf_client.delete(
        reverse("courses_api-detail", kwargs={"pk": course.id})
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_get_course_runs(user_drf_client, course_runs):
    """Test the view that handles requests for all CourseRuns"""
    resp = user_drf_client.get(reverse("course_runs_api-list"))
    course_runs_data = resp.json()
    assert len(course_runs_data) == len(course_runs)
    # Force sorting by run id since this test has been flaky
    course_runs_data = sorted(course_runs_data, key=op.itemgetter("id"))
    for course_run, course_run_data in zip(course_runs, course_runs_data):
        assert course_run_data == CourseRunSerializer(course_run).data


def test_get_course_run(user_drf_client, course_runs):
    """Test the view that handles a request for single CourseRun"""
    course_run = course_runs[0]
    resp = user_drf_client.get(
        reverse("course_runs_api-detail", kwargs={"pk": course_run.id})
    )
    course_run_data = resp.json()
    assert course_run_data == CourseRunSerializer(course_run).data


def test_create_course_run(user_drf_client, course_runs):
    """Test the view that handles a request to create a CourseRun"""
    course_run = course_runs[0]
    course_run_data = CourseRunSerializer(course_run).data
    del course_run_data["id"]
    course_run_data.update(
        {
            "title": "New CourseRun Title",
            "courseware_id": "new-courserun-id",
            "courseware_url_path": "http://example.com",
        }
    )
    request_url = reverse("course_runs_api-list")
    resp = user_drf_client.post(request_url, course_run_data)
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_patch_course_run(user_drf_client, course_runs):
    """Test the view that handles a request to patch a CourseRun"""
    course_run = course_runs[0]
    request_url = reverse("course_runs_api-detail", kwargs={"pk": course_run.id})
    resp = user_drf_client.patch(request_url, {"title": "New CourseRun Title"})
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_delete_course_run(user_drf_client, course_runs):
    """Test the view does not handle a request to delete a CourseRun"""
    course_run = course_runs[0]
    resp = user_drf_client.delete(
        reverse("course_runs_api-detail", kwargs={"pk": course_run.id})
    )
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.parametrize("is_enrolled", [True, False])
@pytest.mark.parametrize("has_unexpired_run", [True, False])
@pytest.mark.parametrize("has_product", [True, False])
@pytest.mark.parametrize("is_anonymous", [True, False])
def test_course_view(  # noqa: PLR0913
    client, user, home_page, is_enrolled, has_unexpired_run, has_product, is_anonymous
):
    """
    Test that the course detail view has the right context and shows the right HTML for the enroll/view button
    """
    course = CourseFactory.create(live=True, page__parent=home_page)

    if has_unexpired_run:
        run = CourseRunFactory.create(course=course, live=True)
    else:
        run = None
    if has_product and has_unexpired_run:
        product_id = ProductVersionFactory.create(
            product=ProductFactory(content_object=run)
        ).product.id
    else:
        product_id = None
    if is_enrolled and has_unexpired_run:
        CourseRunEnrollmentFactory.create(user=user, run=run)

    if not is_anonymous:
        client.force_login(user)
    resp = client.get(course.page.get_url())
    assert resp.context["user"] == user if not is_anonymous else AnonymousUser()
    assert resp.context["product_id"] == product_id
    assert resp.context["enrolled"] == (
        is_enrolled and has_unexpired_run and not is_anonymous
    )

    # Anynoymous users don't see the enrolled/enroll-now button.
    # For logged in users:
    # a) product should exist, next courserun should be there, user not enrolled (enroll now button)
    # b) user is enrolled (enrolled button)
    # NOTE: added `has_unexpired_run` to test for case (b) only because of the way the test is written,
    #       enrollment isn't actually created unless the course has an unexpired run.
    has_button = (
        (has_product and has_unexpired_run and not is_enrolled)
        or (is_enrolled and has_unexpired_run)
    ) and not is_anonymous
    url = ""  # make linter happy
    class_name = ""
    if not is_anonymous:
        if not is_enrolled and has_product and has_unexpired_run:
            url = f"{reverse('checkout-page')}?product={product_id}"
            class_name = "enroll-now"
        if is_enrolled and has_unexpired_run:
            url = reverse("user-dashboard")
            class_name = "enrolled"

    # Note: UTF-8 is the default encoding in Python 3.
    assert (
        f'<a class="enroll-button {class_name}" href="{url}">'.encode() in resp.content
    ) is has_button
    assert (b"Please Sign In to MITx PRO to enroll in a course" in resp.content) is (
        is_anonymous and has_product and has_unexpired_run
    )


@pytest.mark.parametrize("is_enrolled", [True, False])
@pytest.mark.parametrize("has_product", [True, False])
@pytest.mark.parametrize("has_unexpired_run", [True, False])
@pytest.mark.parametrize("is_anonymous", [True, False])
def test_program_view(  # noqa: PLR0913
    client, user, home_page, is_enrolled, has_product, has_unexpired_run, is_anonymous
):
    """
    Test that the program detail view has the right context and shows the right HTML for the enroll/view button
    """
    program = ProgramFactory.create(live=True, page__parent=home_page)

    if has_unexpired_run:
        now = now_in_utc()
        CourseRunFactory.create_batch(
            3,
            course=CourseFactory.create(
                program=program, live=True, position_in_program=1
            ),
            live=True,
            start_date=now + timedelta(hours=2),
        )

    if has_product:
        product_id = ProductVersionFactory.create(
            product=ProductFactory(content_object=program)
        ).product.id
    else:
        product_id = None
    if is_enrolled:
        ProgramEnrollmentFactory.create(user=user, program=program)

    if not is_anonymous:
        client.force_login(user)
    resp = client.get(program.page.get_url())
    assert resp.context["user"] == user if not is_anonymous else AnonymousUser()
    assert resp.context["product_id"] == product_id
    assert resp.context["enrolled"] == (is_enrolled and not is_anonymous)

    # Anynoymous users don't see the enrolled/enroll-now button.
    # For logged in users:
    # a) product should exist, next courserun should be there, user not enrolled (enroll now button)
    # b) user is enrolled (enrolled button)
    has_button = (
        (has_product and has_unexpired_run and not is_enrolled) or is_enrolled
    ) and not is_anonymous
    url = ""  # make linter happy
    class_name = ""
    if not is_anonymous:
        if not is_enrolled and has_product and has_unexpired_run:
            url = f"{reverse('checkout-page')}?product={product_id}"
            class_name = "enroll-now"
        if is_enrolled:
            url = reverse("user-dashboard")
            class_name = "enrolled"

    # Note: UTF-8 is the default encoding in Python 3.
    assert (
        f'<a class="enroll-button {class_name}" href="{url}">'.encode() in resp.content
    ) is has_button
    assert (b"Please Sign In to MITx PRO to enroll in a course" in resp.content) is (
        is_anonymous and has_product and has_unexpired_run
    )


def test_user_enrollments_view(mocker, client, user):
    """
    Test that UserEnrollmentsView returns serialized information about a user's enrollments
    """
    user_enrollments = UserEnrollments(
        programs=[],
        past_programs=[],
        program_runs=[],
        non_program_runs=[],
        past_non_program_runs=[],
    )
    patched_get_user_enrollments = mocker.patch(
        "courses.views.v1.get_user_enrollments", return_value=user_enrollments
    )
    patched_program_enroll_serializer = mocker.patch(
        "courses.views.v1.ProgramEnrollmentSerializer",
        return_value=mocker.Mock(data=[{"program": "enrollment"}]),
    )
    patched_course_enroll_serializer = mocker.patch(
        "courses.views.v1.CourseRunEnrollmentSerializer",
        return_value=mocker.Mock(data=[{"courserun": "enrollment"}]),
    )

    client.force_login(user)
    resp = client.get(reverse("user-enrollments"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "program_enrollments": [{"program": "enrollment"}],
        "course_run_enrollments": [{"courserun": "enrollment"}],
        "past_course_run_enrollments": [{"courserun": "enrollment"}],
        "past_program_enrollments": [{"program": "enrollment"}],
    }

    patched_get_user_enrollments.assert_called_with(user)
    assert patched_program_enroll_serializer.call_count == 2
    assert patched_course_enroll_serializer.call_count == 2


@pytest.mark.parametrize("live", [True, False])
def test_programs_not_live(client, live):
    """Programs should be filtered out if live=False"""
    program = ProgramFactory.create(live=live)
    ProductVersionFactory.create(product=ProductFactory(content_object=program))
    resp = client.get(reverse("programs_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json(), [ProgramSerializer(program).data] if live else []
    )


@pytest.mark.parametrize("live", [True, False])
def test_courses_not_live_in_programs_api(client, live):
    """Courses should be filtered out of the programs API if not live"""
    course = CourseFactory.create(live=live, program__live=True)
    ProductVersionFactory.create(product=ProductFactory(content_object=course.program))
    resp = client.get(reverse("programs_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json()[0]["courses"], [CourseSerializer(course).data] if live else []
    )


@pytest.mark.parametrize("live", [True, False])
def test_courses_not_live_in_courses_api(client, live):
    """Courses should be filtered out of the courses API if not live"""
    course = CourseFactory.create(live=live)
    resp = client.get(reverse("courses_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(resp.json(), [CourseSerializer(course).data] if live else [])


@pytest.mark.parametrize("live", [True, False])
def test_course_runs_not_live_in_courses_api(client, live):
    """Course runs should be filtered out of the courses API if not live"""
    run = CourseRunFactory.create(live=live, course__live=True)
    ProductVersionFactory.create(product=ProductFactory(content_object=run))
    resp = client.get(reverse("courses_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json()[0]["courseruns"], [CourseRunSerializer(run).data] if live else []
    )


@pytest.mark.parametrize("has_product", [True, False])
def test_course_runs_without_product_in_courses_api(client, has_product):
    """Course runs should be filtered out of the courses API if they don't have an associated product"""
    run = CourseRunFactory.create(live=True, course__live=True)
    if has_product:
        ProductVersionFactory.create(product=ProductFactory(content_object=run))
    resp = client.get(reverse("courses_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json()[0]["courseruns"],
        [CourseRunSerializer(run).data] if has_product else [],
    )


@pytest.mark.parametrize("has_product", [True, False])
def test_program_without_product_in_programs_api(client, has_product):
    """Programs should be filtered out of the programs API if they don't have an associated product"""
    program = ProgramFactory.create(live=True)
    if has_product:
        ProductVersionFactory.create(product=ProductFactory(content_object=program))
    resp = client.get(reverse("programs_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json(), [ProgramSerializer(program).data] if has_product else []
    )


@pytest.mark.parametrize("has_product", [True, False])
def test_course_runs_without_product_in_programs_api(client, has_product):
    """Regardless of whether course runs have a product, runs should **not** be filtered out of the programs API"""
    run = CourseRunFactory.create(live=True, course__live=True)
    ProductVersionFactory.create(
        product=ProductFactory(content_object=run.course.program)
    )
    if has_product:
        ProductVersionFactory.create(product=ProductFactory(content_object=run))
    resp = client.get(reverse("programs_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert_drf_json_equal(
        resp.json()[0]["courses"][0]["courseruns"], [CourseRunSerializer(run).data]
    )


@pytest.mark.parametrize(
    "factory, serializer_cls, api_name",  # noqa: PT006
    [
        (
            CourseRunCertificateFactory,
            CourseRunCertificateSerializer,
            "course_run_certificates_api",
        ),
        (
            ProgramCertificateFactory,
            ProgramCertificateSerializer,
            "program_certificates_api",
        ),
    ],
)
def test_course_run_certificate_api(  # noqa: PLR0913
    settings, user, user_drf_client, factory, serializer_cls, api_name
):
    """Verify that the certificates APIs function as expected"""
    settings.MITOL_DIGITAL_CREDENTIALS_AUTH_TYPE = "xpro"
    settings.MITOL_DIGITAL_CREDENTIALS_DEEP_LINK_URL = "http://localhost"

    cert = factory.create(user=user)

    resp = user_drf_client.get(reverse(f"{api_name}-list"))
    assert resp.json() == [serializer_cls(cert).data]

    resp = user_drf_client.get(
        reverse(f"{api_name}-detail", kwargs=dict(uuid=cert.uuid))  # noqa: C408
    )
    assert resp.json() == serializer_cls(cert).data

    assert DigitalCredentialRequest.objects.count() == 0

    resp = user_drf_client.post(
        reverse(f"{api_name}-request_digital_credentials", kwargs=dict(uuid=cert.uuid))  # noqa: C408
    )

    assert DigitalCredentialRequest.objects.count() == 1

    dcr = DigitalCredentialRequest.objects.first()

    assert dcr.learner == user
    assert dcr.credentialed_object == cert

    assert resp.json() == DigitalCredentialRequestSerializer(dcr).data


def test_course_topics_api(client, django_assert_num_queries):
    """
    Test that course topics API returns the expected topics and correct course count.
    """
    resp = client.get(reverse("parent_course_topics_api-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()) == 0

    parent_topic = CourseTopicFactory.create()
    child_topic = CourseTopicFactory.create(parent=parent_topic)
    parent_topic_with_expired_courses = CourseTopicFactory.create()
    child_topic_with_expired_courses = CourseTopicFactory.create(
        parent=parent_topic_with_expired_courses
    )

    now = now_in_utc()
    future_start_date = now + timedelta(days=2)
    future_end_date = now + timedelta(days=10)
    past_start_date = now - timedelta(days=10)
    past_end_date = now - timedelta(days=2)

    future_runs = CourseRunFactory.create_batch(
        2,
        course__live=True,
        start_date=future_start_date,
        end_date=future_end_date,
        live=True,
    )
    past_runs = CourseRunFactory.create_batch(
        2,
        course__live=True,
        start_date=past_start_date,
        end_date=past_end_date,
        enrollment_end=None,
        live=True,
    )

    live_external_course_pages = ExternalCoursePageFactory.create_batch(2, live=True)
    for external_course_page in live_external_course_pages:
        CourseRunFactory.create(
            course=external_course_page.course,
            start_date=future_start_date,
            end_date=future_end_date,
            live=True,
        )

    expired_external_course_pages = ExternalCoursePageFactory.create_batch(2, live=True)
    for external_course_page in expired_external_course_pages:
        CourseRunFactory.create(
            course=external_course_page.course,
            start_date=past_start_date,
            end_date=past_end_date,
            enrollment_end=None,
            live=True,
        )

    for run, topic in zip(future_runs, [parent_topic, child_topic]):
        run.course.coursepage.topics.set([topic.id])

    for run, topic in zip(past_runs, [parent_topic, child_topic]):
        run.course.coursepage.topics.set([topic.id])

    for external_course_page, topic in zip(
        live_external_course_pages, [parent_topic, child_topic]
    ):
        external_course_page.topics.set([topic.id])

    for external_course_page, topic in zip(
        expired_external_course_pages,
        [parent_topic_with_expired_courses, child_topic_with_expired_courses],
    ):
        external_course_page.topics.set([topic.id])

    with django_assert_num_queries(2):
        resp = client.get(reverse("parent_course_topics_api-list"))
        assert resp.status_code == status.HTTP_200_OK

        resp_json = resp.json()
        assert len(resp_json) == 1
        assert resp_json[0]["name"] == parent_topic.name
        assert resp_json[0]["course_count"] == 4


@pytest.mark.parametrize("expected_status_code", [200, 500])
@pytest.mark.parametrize(
    "vendor_name", [EMERITUS_PLATFORM_NAME, GLOBAL_ALUMNI_PLATFORM_NAME]
)
def test_external_course_list_view(
    admin_drf_client, mocker, expected_status_code, vendor_name
):
    """
    Test that the External API List calls fetch_external_courses and returns its mocked response.
    """
    if expected_status_code == 200:
        with Path(
            "courses/sync_external_courses/test_data/batch_test.json"
        ).open() as test_data_file:
            mocked_response = json.load(test_data_file)["rows"]

        patched_fetch_external_courses = mocker.patch(
            "courses.views.v1.fetch_external_courses", return_value=mocked_response
        )
    else:
        patched_fetch_external_courses = mocker.patch(
            "courses.views.v1.fetch_external_courses",
            side_effect=Exception("Some error occurred."),
        )
        mocked_response = {
            "error": "Some error occurred.",
            "details": "Some error occurred.",
        }

    response = admin_drf_client.get(
        reverse("external_courses", kwargs={"vendor": vendor_name})
    )
    assert response.json() == mocked_response
    assert response.status_code == expected_status_code
    patched_fetch_external_courses.assert_called_once()

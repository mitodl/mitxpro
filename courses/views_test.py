"""
Tests for course views
"""
# pylint: disable=unused-argument, redefined-outer-name
import operator as op
from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework import status

from courses.api import UserEnrollments
from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    ProgramFactory,
    CourseRunEnrollmentFactory,
    ProgramEnrollmentFactory,
)
from courses.serializers import CourseRunSerializer, CourseSerializer, ProgramSerializer
from ecommerce.factories import ProductFactory, ProductVersionFactory
from mitxpro.test_utils import assert_drf_json_equal
from mitxpro.utils import now_in_utc

pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def programs():
    """Fixture for a set of Programs in the database"""
    programs = ProgramFactory.create_batch(3)
    for program in programs:
        ProductVersionFactory.create(product=ProductFactory(content_object=program))
    return programs


@pytest.fixture()
def courses():
    """Fixture for a set of Courses in the database"""
    return CourseFactory.create_batch(3)


@pytest.fixture()
def course_runs():
    """Fixture for a set of CourseRuns in the database"""
    return CourseRunFactory.create_batch(3)


def test_get_programs(user_drf_client, programs):
    """Test the view that handles requests for all Programs"""
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
    if is_anonymous:
        user_drf_client.logout()
    resp = user_drf_client.get(reverse("courses_api-list"))
    courses_data = resp.json()
    assert len(courses_data) == len(courses)
    for course, course_data in zip(courses, courses_data):
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


# pylint: disable=too-many-arguments
@pytest.mark.parametrize("is_enrolled", [True, False])
@pytest.mark.parametrize("has_unexpired_run", [True, False])
@pytest.mark.parametrize("has_product", [True, False])
@pytest.mark.parametrize("is_anonymous", [True, False])
def test_course_view(
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
            url = f'{reverse("checkout-page")}?product={product_id}'
            class_name = "enroll-now"
        if is_enrolled and has_unexpired_run:
            url = reverse("user-dashboard")
            class_name = "enrolled"

    assert (
        f'<a class="enroll-button {class_name}" href="{url}">'.encode("utf-8")
        in resp.content
    ) is has_button
    assert (
        "Please Sign In to MITx PRO to enroll in a course".encode("utf-8")
        in resp.content
    ) is (is_anonymous and has_product and has_unexpired_run)


@pytest.mark.parametrize("is_enrolled", [True, False])
@pytest.mark.parametrize("has_product", [True, False])
@pytest.mark.parametrize("has_unexpired_run", [True, False])
@pytest.mark.parametrize("is_anonymous", [True, False])
def test_program_view(
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
            url = f'{reverse("checkout-page")}?product={product_id}'
            class_name = "enroll-now"
        if is_enrolled:
            url = reverse("user-dashboard")
            class_name = "enrolled"

    assert (
        f'<a class="enroll-button {class_name}" href="{url}">'.encode("utf-8")
        in resp.content
    ) is has_button
    assert (
        "Please Sign In to MITx PRO to enroll in a course".encode("utf-8")
        in resp.content
    ) is (is_anonymous and has_product and has_unexpired_run)


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

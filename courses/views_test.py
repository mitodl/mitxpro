"""
Tests for course views
"""
# pylint: disable=unused-argument, redefined-outer-name
import operator as op
import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework import status

from courses.factories import (
    ProgramFactory,
    CourseFactory,
    CourseRunEnrollment,
    CourseRunFactory,
)
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from courses.api import UserEnrollments
from ecommerce.factories import ProductFactory, ProductVersionFactory


pytestmark = [pytest.mark.django_db]


@pytest.fixture()
def programs():
    """Fixture for a set of Programs in the database"""
    return ProgramFactory.create_batch(3)


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
        assert program_data == ProgramSerializer(program).data


def test_get_program(user_drf_client, programs):
    """Test the view that handles a request for single Program"""
    program = programs[0]
    resp = user_drf_client.get(
        reverse("programs_api-detail", kwargs={"pk": program.id})
    )
    program_data = resp.json()
    assert program_data == ProgramSerializer(program).data


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


def test_get_courses(user_drf_client, courses):
    """Test the view that handles requests for all Courses"""
    resp = user_drf_client.get(reverse("courses_api-list"))
    courses_data = resp.json()
    assert len(courses_data) == len(courses)
    for course, course_data in zip(courses, courses_data):
        assert course_data == CourseSerializer(course).data


def test_get_course(user_drf_client, courses):
    """Test the view that handles a request for single Course"""
    course = courses[0]
    resp = user_drf_client.get(reverse("courses_api-detail", kwargs={"pk": course.id}))
    course_data = resp.json()
    assert course_data == CourseSerializer(course).data


def test_create_course(user_drf_client, courses):
    """Test the view that handles a request to create a Course"""
    course = courses[0]
    course_data = CourseSerializer(course).data
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


def test_course_catalog_view(client):
    """
    Test that the course catalog view fetches live programs/courses and serializes
    them for the catalog template.
    """
    program = ProgramFactory.create(live=True)
    course_in_program = CourseFactory.create(program=program, live=True)
    course_no_program = CourseFactory.create(no_program=True, live=True)
    CourseFactory.create(no_program=True, live=False)
    exp_programs = [program]
    exp_courses = [course_in_program, course_no_program]
    resp = client.get(reverse("mitxpro-catalog"))
    assert resp.templates[0].name == "catalog.html"
    assert list(resp.context["programs"]) == exp_programs
    assert list(resp.context["courses"]) == exp_courses


@pytest.mark.parametrize("is_enrolled", [True, False])
@pytest.mark.parametrize("has_unexpired_run", [True, False])
@pytest.mark.parametrize("has_product", [True, False])
@pytest.mark.parametrize("is_anonymous", [True, False])
def test_course_view(
    client, user, is_enrolled, has_unexpired_run, has_product, is_anonymous
):
    """
    Test that the course detail view has the right context and shows the right HTML for the enroll/view button
    """
    course = CourseFactory.create(live=True)
    if has_unexpired_run:
        run = CourseRunFactory.create(course=course)
    else:
        run = None
    if has_product and has_unexpired_run:
        product_version_id = ProductVersionFactory.create(
            product=ProductFactory(content_object=run)
        ).id
    else:
        product_version_id = None
    if is_enrolled and has_unexpired_run:
        CourseRunEnrollment.objects.create(user=user, run=run)

    if not is_anonymous:
        client.force_login(user)
    resp = client.get(reverse("course-detail", kwargs={"pk": course.id}))
    assert resp.context["course"] == course
    assert resp.context["user"] == user if not is_anonymous else AnonymousUser()
    assert resp.context["courseware_url"] == (run.courseware_url if run else None)
    assert resp.context["product_version_id"] == (
        product_version_id if not is_anonymous else None
    )
    assert resp.context["enrolled"] == (
        is_enrolled and has_unexpired_run and not is_anonymous
    )

    has_button = False
    url = ""  # make linter happy
    if not is_anonymous:
        if not is_enrolled and has_product and has_unexpired_run:
            url = f'{reverse("checkout-page")}?product={product_version_id}'
            has_button = True
        if is_enrolled and has_unexpired_run:
            url = reverse("user-dashboard")
            has_button = True

    assert (
        f'<a class="enroll-button" href="{url}">'.encode("utf-8") in resp.content
    ) is has_button


def test_user_enrollments_view(mocker, client, user):
    """
    Test that UserEnrollmentsView returns serialized information about a user's enrollments
    """
    user_enrollments = UserEnrollments(
        programs=[], program_runs=[], non_program_runs=[]
    )
    patched_get_user_enrollments = mocker.patch(
        "courses.views.get_user_enrollments", return_value=user_enrollments
    )
    patched_program_enroll_serializer = mocker.patch(
        "courses.views.ProgramEnrollmentSerializer",
        return_value=mocker.Mock(data=[{"program": "enrollment"}]),
    )
    patched_course_enroll_serializer = mocker.patch(
        "courses.views.CourseRunEnrollmentSerializer",
        return_value=mocker.Mock(data=[{"courserun": "enrollment"}]),
    )

    client.force_login(user)
    resp = client.get(reverse("user-enrollments"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "program_enrollments": [{"program": "enrollment"}],
        "course_run_enrollments": [{"courserun": "enrollment"}],
    }
    patched_get_user_enrollments.assert_called_with(user)
    patched_program_enroll_serializer.assert_called_once()
    patched_course_enroll_serializer.assert_called_once()

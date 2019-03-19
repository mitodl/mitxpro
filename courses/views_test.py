"""
Tests for course views
"""
# pylint: disable=unused-argument, redefined-outer-name
import pytest
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from courses.factories import ProgramFactory, CourseFactory, CourseRunFactory
from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer


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
    programs_data = resp.json()
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
    del program_data["thumbnail"]
    program_data["title"] = "New Program Title"
    request_url = reverse("programs_api-list")
    resp = user_drf_client.post(request_url, program_data)
    assert resp.status_code == HTTP_201_CREATED


def test_patch_program(user_drf_client, programs):
    """Test the view that handles a request to patch a Program"""
    program = programs[0]
    request_url = reverse("programs_api-detail", kwargs={"pk": program.id})
    resp = user_drf_client.patch(request_url, {"title": "New Program Title"})
    assert resp.status_code == HTTP_200_OK
    resp_data = resp.json()
    program.refresh_from_db()
    assert program.title == "New Program Title"
    assert resp_data == ProgramSerializer(program).data


def test_delete_program(user_drf_client, programs):
    """Test the view that handles a request to delete a Program"""
    program = programs[0]
    resp = user_drf_client.delete(
        reverse("programs_api-detail", kwargs={"pk": program.id})
    )
    assert resp.status_code == HTTP_204_NO_CONTENT
    with pytest.raises(Program.DoesNotExist):
        program.refresh_from_db()


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
    del course_data["thumbnail"]
    course_data["title"] = "New Course Title"
    request_url = reverse("courses_api-list")
    resp = user_drf_client.post(request_url, course_data)
    assert resp.status_code == HTTP_201_CREATED


def test_patch_course(user_drf_client, courses):
    """Test the view that handles a request to patch a Course"""
    course = courses[0]
    request_url = reverse("courses_api-detail", kwargs={"pk": course.id})
    resp = user_drf_client.patch(request_url, {"title": "New Course Title"})
    assert resp.status_code == HTTP_200_OK
    resp_data = resp.json()
    course.refresh_from_db()
    assert course.title == "New Course Title"
    assert resp_data == CourseSerializer(course).data


def test_delete_course(user_drf_client, courses):
    """Test the view that handles a request to delete a Course"""
    course = courses[0]
    resp = user_drf_client.delete(
        reverse("courses_api-detail", kwargs={"pk": course.id})
    )
    assert resp.status_code == HTTP_204_NO_CONTENT
    with pytest.raises(Course.DoesNotExist):
        course.refresh_from_db()


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
            "courseware_url": "http://example.com",
        }
    )
    request_url = reverse("course_runs_api-list")
    resp = user_drf_client.post(request_url, course_run_data)
    assert resp.status_code == HTTP_201_CREATED


def test_patch_course_run(user_drf_client, course_runs):
    """Test the view that handles a request to patch a CourseRun"""
    course_run = course_runs[0]
    request_url = reverse("course_runs_api-detail", kwargs={"pk": course_run.id})
    resp = user_drf_client.patch(request_url, {"title": "New CourseRun Title"})
    assert resp.status_code == HTTP_200_OK
    resp_data = resp.json()
    course_run.refresh_from_db()
    assert course_run.title == "New CourseRun Title"
    assert resp_data == CourseRunSerializer(course_run).data


def test_delete_course_run(user_drf_client, course_runs):
    """Test the view that handles a request to delete a CourseRun"""
    course_run = course_runs[0]
    resp = user_drf_client.delete(
        reverse("course_runs_api-detail", kwargs={"pk": course_run.id})
    )
    assert resp.status_code == HTTP_204_NO_CONTENT
    with pytest.raises(CourseRun.DoesNotExist):
        course_run.refresh_from_db()


def test_course_catalog_view(client):
    """
    Test that the course catalog view fetches live programs/courses and serializes
    them for the catalog template.
    """
    program = ProgramFactory.create(live=True)
    course_in_program = CourseFactory.create(program=program, live=True)
    course_no_program = CourseFactory.create(no_program=True, live=True)
    CourseFactory.create(no_program=True, live=False)
    exp_courseware_objects = [
        ProgramSerializer(program).data,
        CourseSerializer(course_in_program).data,
        CourseSerializer(course_no_program).data,
    ]
    resp = client.get(reverse("mitxpro-index"))
    assert resp.templates[0].name == "catalog.html"
    assert list(resp.context["courseware_objects"]) == exp_courseware_objects

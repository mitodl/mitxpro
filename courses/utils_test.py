# pylint:disable=redefined-outer-name
"""
Tests for signals
"""
from unittest.mock import Mock

from edx_api.course_detail import CourseDetail, CourseDetails
from requests.exceptions import HTTPError

import pytest
from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunFactory,
    CourseRunGradeFactory,
    ProgramCertificateFactory,
    ProgramFactory,
    UserFactory,
)
from courses.models import ProgramCertificate
from courses.utils import (
    generate_program_certificate,
    process_course_run_grade_certificate,
    sync_course_runs,
)

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user():
    """User object fixture"""
    return UserFactory.create()


@pytest.fixture()
def program():
    """User object fixture"""
    return ProgramFactory.create()


@pytest.fixture()
def course():
    """Course object fixture"""
    return CourseFactory.create()


# pylint: disable=too-many-arguments
@pytest.mark.parametrize(
    "grade, passed, exp_certificate, exp_created, exp_deleted",
    [
        [0.25, True, True, True, False],
        [0.0, True, False, False, False],
        [1.0, False, False, False, False],
    ],
)
def test_course_run_certificate(
    user, course, grade, passed, exp_certificate, exp_created, exp_deleted
):
    """
    Test that the certificate is generated correctly
    """
    certificate, created, deleted = process_course_run_grade_certificate(
        CourseRunGradeFactory.create(
            course_run__course=course, user=user, grade=grade, passed=passed
        )
    )
    assert bool(certificate) is exp_certificate
    assert created is exp_created
    assert deleted is exp_deleted


def test_course_run_certificate_idempotent(user, course):
    """
    Test that the certificate generation is idempotent
    """
    grade = CourseRunGradeFactory.create(
        course_run__course=course, user=user, grade=0.25, passed=True
    )

    # Certificate is created the first time
    certificate, created, deleted = process_course_run_grade_certificate(grade)
    assert certificate
    assert created
    assert not deleted

    # Existing certificate is simply returned without any create/delete
    certificate, created, deleted = process_course_run_grade_certificate(grade)
    assert certificate
    assert not created
    assert not deleted


def test_course_run_certificate_not_passing(user, course):
    """
    Test that the certificate is not generated if the grade is set to 0.0
    """
    grade = CourseRunGradeFactory.create(
        course_run__course=course, user=user, grade=1.0, passed=True
    )

    # Initially the certificate is created
    certificate, created, deleted = process_course_run_grade_certificate(grade)
    assert certificate
    assert created
    assert not deleted

    # Now that the grade indicates score 0.0, certificate should be deleted
    grade.grade = 0.0
    certificate, created, deleted = process_course_run_grade_certificate(grade)
    assert not certificate
    assert not created
    assert deleted


def test_generate_program_certificate_already_exist(user, program):
    """
    Test that generate_program_certificate return (None, False) and not create program certificate
    if program certificate already exist.
    """
    program_certificate = ProgramCertificateFactory.create(program=program, user=user)
    result = generate_program_certificate(user=user, program=program)
    assert result == (program_certificate, False)
    assert len(ProgramCertificate.objects.all()) == 1


def test_generate_program_certificate_failure(user, program):
    """
    Test that generate_program_certificate return (None, False) and not create program certificate
    if there is not any course_run certificate for the given course.
    """
    course = CourseFactory.create(program=program)
    CourseRunFactory.create_batch(3, course=course)

    result = generate_program_certificate(user=user, program=program)
    assert result == (None, False)
    assert len(ProgramCertificate.objects.all()) == 0


def test_generate_program_certificate_success(user, program):
    """
    Test that generate_program_certificate generate a program certificate
    """
    course = CourseFactory.create(program=program)
    course_run = CourseRunFactory.create(course=course)

    CourseRunCertificateFactory.create(user=user, course_run=course_run)

    result = generate_program_certificate(user=user, program=program)
    assert result[1] is True
    assert isinstance(result[0], ProgramCertificate)
    assert len(ProgramCertificate.objects.all()) == 1


@pytest.mark.parametrize(
    "mocked_api_response, expect_success",
    [
        [
            CourseDetail(
                {
                    "id": "course-v1:edX+DemoX+2020_T1",
                    "start": "2019-01-01T00:00:00Z",
                    "end": "2020-02-01T00:00:00Z",
                    "enrollment_start": "2019-01-01T00:00:00Z",
                    "enrollment_end": "2020-02-01T00:00:00Z",
                    "name": "Demonstration Course",
                }
            ),
            True,
        ],
        [
            CourseDetail(
                {
                    "id": "course-v1:edX+DemoX+2020_T1",
                    "start": "2021-01-01T00:00:00Z",
                    "end": "2020-02-01T00:00:00Z",
                    "enrollment_start": None,
                    "enrollment_end": None,
                    "name": None,
                }
            ),
            False,
        ],
        [HTTPError(response=Mock(status_code=404)), False],
        [HTTPError(response=Mock(status_code=400)), False],
        [ConnectionError(), False],
    ],
)
def test_sync_course_runs(settings, mocker, mocked_api_response, expect_success):
    """
    Test that sync_course_runs fetches data from edX API. Should fail on API responding with
    an error, as well as trying to set the course run title to None
    """
    settings.OPENEDX_SERVICE_WORKER_API_TOKEN = "mock_api_token"
    mocker.patch.object(CourseDetails, "get_detail", side_effect=[mocked_api_response])
    course_run = CourseRunFactory.create()

    success_count, failure_count = sync_course_runs([course_run])

    if expect_success:
        course_run.refresh_from_db()
        assert success_count == 1
        assert failure_count == 0
        assert course_run.title == mocked_api_response.name
        assert course_run.start_date == mocked_api_response.start
        assert course_run.end_date == mocked_api_response.end
        assert course_run.enrollment_start == mocked_api_response.enrollment_start
        assert course_run.enrollment_end == mocked_api_response.enrollment_end
    else:
        assert success_count == 0
        assert failure_count == 1

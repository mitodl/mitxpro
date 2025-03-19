"""
Tests for signals
"""

from datetime import timedelta

from unittest.mock import Mock

import factory
import pytest
from edx_api.course_detail import CourseDetail, CourseDetails
from requests.exceptions import HTTPError

from courses.factories import (
    CourseFactory,
    CourseRunCertificateFactory,
    CourseRunFactory,
    CourseRunGradeFactory,
    ProgramCertificateFactory,
    ProgramFactory,
    UserFactory,
    CourseLanguageFactory,
)
from courses.models import ProgramCertificate
from courses.utils import (
    generate_program_certificate,
    process_course_run_grade_certificate,
    sync_course_runs,
    get_catalog_languages,
)
from mitxpro.utils import now_in_utc

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    """User object fixture"""
    return UserFactory.create()


@pytest.fixture
def program():
    """User object fixture"""
    return ProgramFactory.create()


@pytest.fixture
def course():
    """Course object fixture"""
    return CourseFactory.create()


@pytest.mark.parametrize(
    "grade, passed, exp_certificate, exp_created, exp_deleted",  # noqa: PT006
    [
        [0.25, True, True, True, False],  # noqa: PT007
        [0.0, True, False, False, False],  # noqa: PT007
        [1.0, False, False, False, False],  # noqa: PT007
    ],
)
def test_course_run_certificate(  # noqa: PLR0913
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
    "mocked_api_response, expect_success",  # noqa: PT006
    [
        [  # noqa: PT007
            CourseDetail(
                {
                    "id": "course-v1:edX+DemoX+2020_T1",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                    "name": "Demonstration Course",
                }
            ),
            True,
        ],
        [  # noqa: PT007
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
        [HTTPError(response=Mock(status_code=404)), False],  # noqa: PT007
        [HTTPError(response=Mock(status_code=400)), False],  # noqa: PT007
        [ConnectionError(), False],  # noqa: PT007
    ],
)
def test_sync_course_runs(settings, mocker, mocked_api_response, expect_success):
    """
    Test that sync_course_runs fetches data from edX API. Should fail on API responding with
    an error, as well as trying to set the course run title to None
    """
    settings.OPENEDX_SERVICE_WORKER_API_TOKEN = "mock_api_token"  # noqa: S105
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


def test_catalog_visible_languages():
    """Test that get_catalog_languages returns the expected languages"""

    catalog_visible_languages = CourseLanguageFactory.create_batch(
        2, name=factory.Iterator(["Language1", "Language2"])
    )
    catalog_invisble_languages = CourseLanguageFactory.create_batch(
        2, name=factory.Iterator(["Language3", "Language4"])
    )
    catalog_visible_inactive_languages = CourseLanguageFactory.create_batch(
        2, name=factory.Iterator(["Language5", "Language6"]), is_active=False
    )
    now = now_in_utc()
    # Creates active courses (Course runs will create underlying course and page objects)
    CourseRunFactory.create_batch(
        4,
        start_date=now + timedelta(days=1),
        enrollment_end=now + timedelta(days=2),
        course__page__language=factory.Iterator(catalog_visible_languages),
        course__program__page__language=factory.Iterator(
            catalog_visible_languages + catalog_visible_inactive_languages
        ),
    )
    # Creates expired courses (Course runs will create underlying course and page objects)
    CourseRunFactory.create_batch(
        2,
        start_date=now - timedelta(days=1),
        enrollment_end=now - timedelta(days=2),
        course__page__language=factory.Iterator(catalog_invisble_languages),
        course__program__page__language=factory.Iterator(catalog_invisble_languages),
        force_insert=True,
    )

    # The expected languages are the ones that are associated with unexpuired/catalog visible courses
    assert get_catalog_languages() == [
        catalog_language.name for catalog_language in catalog_visible_languages
    ]

"""
Tests for signals
"""

from datetime import timedelta
from datetime import datetime
import pytz

import factory
import pytest
from edx_api.course_detail import CourseDetail

from courses.factories import (
    CourseFactory,
    CourseRunFactory,
    CourseRunCertificateFactory,
    CourseRunGradeFactory,
    ProgramFactory,
    ProgramCertificateFactory,
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
    "test_scenario, api_response, course_runs_data, expected_success, expected_failure, expected_unchanged, api_error, save_error_index",
    [
        (
            "empty_list",
            [],
            [],
            0,
            0,
            0,
            None,
            None,
        ),
        (
            "all_successful",
            [
                {
                    "id": "course-v1:edX+DemoX+2020_T1",
                    "name": "Updated Course 1",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                },
                {
                    "id": "course-v1:edX+DemoX+2020_T2",
                    "name": "Updated Course 2",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                },
            ],
            [
                {
                    "courseware_id": "course-v1:edX+DemoX+2020_T1",
                    "title": "Old Course 1",
                },
                {
                    "courseware_id": "course-v1:edX+DemoX+2020_T2",
                    "title": "Old Course 2",
                },
            ],
            2,
            0,
            0,
            None,
            None,
        ),
        (
            "all_unchanged",
            [
                {
                    "id": "course-v1:edX+DemoX+2020_T1",
                    "name": "Existing Course 1",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                },
                {
                    "id": "course-v1:edX+DemoX+2020_T2",
                    "name": "Existing Course 2",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                },
            ],
            [
                {
                    "courseware_id": "course-v1:edX+DemoX+2020_T1",
                    "title": "Existing Course 1",
                },
                {
                    "courseware_id": "course-v1:edX+DemoX+2020_T2",
                    "title": "Existing Course 2",
                },
            ],
            0,
            0,
            2,
            None,
            None,
        ),
        (
            "api_failure",
            [],
            [
                {"courseware_id": "course-v1:edX+DemoX+2020_T1", "title": "Course 1"},
                {"courseware_id": "course-v1:edX+DemoX+2020_T2", "title": "Course 2"},
            ],
            0,
            2,
            0,
            Exception("API connection failed"),
            None,
        ),
        (
            "http_error",
            [],
            [
                {"courseware_id": "course-v1:edX+DemoX+2020_T1", "title": "Course 1"},
                {"courseware_id": "course-v1:edX+DemoX+2020_T2", "title": "Course 2"},
            ],
            0,
            2,
            0,
            "HTTPError",
            None,
        ),
        (
            "unknown_course",
            [
                {
                    "id": "course-v1:edX+DemoX+UNKNOWN",
                    "name": "Unknown Course",
                    "start": "2098-01-01T00:00:00Z",
                    "end": "2099-02-01T00:00:00Z",
                    "enrollment_start": "2098-01-01T00:00:00Z",
                    "enrollment_end": "2099-02-01T00:00:00Z",
                },
            ],
            [
                {
                    "courseware_id": "course-v1:edX+DemoX+2020_T1",
                    "title": "Existing Course",
                },
            ],
            0,
            0,
            0,
            None,
            None,
        ),
    ],
)
def test_sync_course_runs(
    settings,
    mocker,
    test_scenario,
    api_response,
    course_runs_data,
    expected_success,
    expected_failure,
    expected_unchanged,
    api_error,
    save_error_index,
):
    """Test sync_course_runs with various scenarios using parameterization"""
    settings.OPENEDX_SERVICE_WORKER_API_TOKEN = "mock_api_token"  # noqa: S105

    mock_course_list = mocker.Mock()

    if api_error == "HTTPError":
        from requests.exceptions import HTTPError
        from requests import Response

        mock_response = mocker.Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_course_list.get_courses.side_effect = HTTPError(response=mock_response)
    elif api_error:
        mock_course_list.get_courses.side_effect = api_error
    else:
        mocked_course_details = [
            CourseDetail(course_data) for course_data in api_response
        ]
        mock_course_list.get_courses.return_value = mocked_course_details

    mocker.patch(
        "courses.utils.get_edx_api_course_list_client",
        return_value=mock_course_list,
    )

    course_runs = []
    if course_runs_data:
        for course_data in course_runs_data:
            course_run = CourseRunFactory.create(
                courseware_id=course_data["courseware_id"],
                title=course_data["title"],
                start_date=datetime.strptime(
                    "2098-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC),
                end_date=datetime.strptime(
                    "2099-02-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC),
                enrollment_start=datetime.strptime(
                    "2098-01-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC),
                enrollment_end=datetime.strptime(
                    "2099-02-01T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC),
                expiration_date=None,
            )
            course_runs.append(course_run)

    if save_error_index is not None:
        mocker.patch.object(
            course_runs[save_error_index],
            "save",
            side_effect=Exception("Validation error"),
        )

    success_count, failure_count, unchanged_count = sync_course_runs(course_runs)

    if test_scenario == "empty_list":
        mock_course_list.get_courses.assert_not_called()
    elif not api_error:
        expected_course_keys = [
            course_data["courseware_id"] for course_data in course_runs_data
        ]
        mock_course_list.get_courses.assert_called_once_with(
            course_keys=expected_course_keys
        )
    else:
        mock_course_list.get_courses.assert_called_once()

    assert success_count == expected_success
    assert failure_count == expected_failure
    assert unchanged_count == expected_unchanged

    if expected_success > 0 and not api_error:
        for i, course_data in enumerate(course_runs_data):
            course_runs[i].refresh_from_db()

            api_course_data = None
            for api_data in api_response:
                if api_data["id"] == course_data["courseware_id"]:
                    api_course_data = api_data
                    break

            if api_course_data:
                assert course_runs[i].title == api_course_data["name"]
                assert course_runs[i].start_date == datetime.strptime(
                    api_course_data["start"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)
                assert course_runs[i].end_date == datetime.strptime(
                    api_course_data["end"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)
                assert course_runs[i].enrollment_start == datetime.strptime(
                    api_course_data["enrollment_start"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)
                assert course_runs[i].enrollment_end == datetime.strptime(
                    api_course_data["enrollment_end"], "%Y-%m-%dT%H:%M:%SZ"
                ).replace(tzinfo=pytz.UTC)


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

"""Tests for command utils"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model

from courses.factories import (
    CourseRunEnrollmentFactory,
    CourseRunFactory,
    ProgramEnrollmentFactory,
)
from courses.management.utils import EnrollmentChangeCommand
from courseware.exceptions import (
    EdxApiEnrollErrorException,
    UnknownEdxApiEnrollException,
)
from mitxpro.test_utils import MockHttpError
from mitxpro.utils import now_in_utc
from users.factories import UserFactory
from courses.management.utils import update_certificates


User = get_user_model()


@pytest.mark.django_db
@pytest.mark.parametrize("order", [True, False])
def test_fetch_enrollment(order):
    """Test that method return enrollment and enrolled object, include order while querying if passed"""
    user = UserFactory()
    run_enrollment = CourseRunEnrollmentFactory(user=user)
    program_enrollment = ProgramEnrollmentFactory(user=user)

    run_command_options = {"run": run_enrollment.run.courseware_id}
    program_command_options = {"program": program_enrollment.program.readable_id}

    if order:
        run_command_options["order"] = run_enrollment.order
        program_command_options["order"] = program_enrollment.order
    enrollment_obj, enrolled_obj = EnrollmentChangeCommand.fetch_enrollment(
        user=user, command_options=run_command_options
    )

    assert enrolled_obj == run_enrollment.run
    assert enrollment_obj == run_enrollment

    enrollment_obj, enrolled_obj = EnrollmentChangeCommand.fetch_enrollment(
        user=user, command_options=program_command_options
    )

    assert enrolled_obj == program_enrollment.program
    assert enrollment_obj == program_enrollment


@pytest.mark.django_db
@pytest.mark.parametrize("keep_failed_enrollments", [True, False])
@pytest.mark.parametrize(
    "exception_cls,inner_exception",  # noqa: PT006
    [
        [EdxApiEnrollErrorException, MockHttpError()],  # noqa: PT007
        [UnknownEdxApiEnrollException, Exception()],  # noqa: PT007
    ],
)
def test_create_run_enrollment_edx_failure(
    mocker, keep_failed_enrollments, exception_cls, inner_exception
):
    """Test that create_run_enrollment behaves as expected when the enrollment fails in edX"""
    now = now_in_utc()
    user = UserFactory()
    existing_enrollment = CourseRunEnrollmentFactory(user=user)
    non_program_run = CourseRunFactory.create(
        course__no_program=True, start_date=(now + timedelta(days=1))
    )
    expected_enrollment = CourseRunEnrollmentFactory(user=user, run=non_program_run)

    patched_edx_enroll = mocker.patch(
        "courses.management.utils.enroll_in_edx_course_runs",
        side_effect=exception_cls(user, non_program_run, inner_exception),
    )

    new_enrollment = EnrollmentChangeCommand().create_run_enrollment(
        existing_enrollment=existing_enrollment,
        to_user=user,
        to_run=non_program_run,
        keep_failed_enrollments=keep_failed_enrollments,
    )

    patched_edx_enroll.assert_called_once_with(user, [non_program_run])

    if keep_failed_enrollments:
        assert new_enrollment == expected_enrollment
    else:
        assert new_enrollment is None


def test_update_certificates(mocker):
    """Test the update_certificates function to ensure it updates the certificate revisions correctly."""
    mock_model = mocker.Mock()
    mock_cert1 = mocker.Mock(certificate_page_revision=None)
    mock_cert2 = mocker.Mock(certificate_page_revision=None)
    mock_model.objects.filter.return_value = [mock_cert1, mock_cert2]

    mock_latest_revision = mocker.Mock()
    mock_latest_revision.latest_revision = "rev-123"

    mock_children_qs = mocker.Mock()
    mock_type_qs = mocker.Mock()
    mock_live_qs = mocker.Mock()
    mock_ordered_qs = mocker.Mock()

    mock_children_qs.type.return_value = mock_type_qs
    mock_type_qs.live.return_value = mock_live_qs
    mock_live_qs.order_by.return_value = mock_ordered_qs
    mock_ordered_qs.first.return_value = mock_latest_revision

    mock_page = mocker.Mock()
    mock_page.get_children.return_value = mock_children_qs

    mock_stdout = mocker.Mock()

    # Assert initial state (before)
    assert mock_cert1.certificate_page_revision is None
    assert mock_cert2.certificate_page_revision is None

    # Call the function to test
    update_certificates(
        model_cls=mock_model,
        filter_kwargs={"course_run": "run-42"},
        page_getter=lambda: mock_page,
        stdout=mock_stdout,
        label="course run 42"
    )

    # Assert updated state (after)
    assert mock_cert1.certificate_page_revision == "rev-123"
    assert mock_cert2.certificate_page_revision == "rev-123"

    # Assert bulk update was called correctly
    mock_model.objects.bulk_update.assert_called_once_with(
        [mock_cert1, mock_cert2], ["certificate_page_revision"]
    )

    # Assert stdout
    mock_stdout.write.assert_called_once_with(
        "Successfully updated 2 course run 42 certificate(s) to latest revision."
    )

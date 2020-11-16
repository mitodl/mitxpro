"""
Signals for micromasters course certificates
"""
from typing import Type, Union, Any

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.credentials import create_and_notify_digital_credential_request
from courses.models import CourseRunCertificate, ProgramCertificate
from courses.utils import generate_program_certificate


@receiver(
    post_save,
    sender=CourseRunCertificate,
    dispatch_uid="courseruncertificate_post_save",
)
def handle_create_course_run_certificate(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    When a CourseRunCertificate model is created.
    """
    if created:
        user = instance.user
        program = instance.course_run.course.program
        if program:
            transaction.on_commit(lambda: generate_program_certificate(user, program))


@receiver(
    post_save,
    sender=CourseRunCertificate,
    dispatch_uid="create_course_run_digital_credential_request",
)
@receiver(
    post_save,
    sender=ProgramCertificate,
    dispatch_uid="create_program_digital_credential_request",
)
def create_digital_credential_request(
    sender: Union[Type[CourseRunCertificate], Type[ProgramCertificate]],
    instance: Union[CourseRunCertificate, ProgramCertificate],
    created: bool,
    **kwargs: Any,
):  # pylint: disable=unused-argument
    """Create a digital credential request for """
    if created:
        create_and_notify_digital_credential_request(instance)

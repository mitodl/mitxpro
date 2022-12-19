"""
Signals for micromasters course certificates
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from caching.api import invalidate_course_cache
from courses.models import CourseRunCertificate, Course, CourseRun, Program
from courses.utils import generate_program_certificate
from cms.models import ProgramPage
from ecommerce.models import Product, ProductVersion


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


@receiver(post_save, sender=Course)
@receiver(post_save, sender=CourseRun)
@receiver(post_save, sender=Program)
@receiver(post_save, sender=ProgramPage)
@receiver(post_save, sender=Product)
def handle_course_cache_invalidation(sender, instance, created, **kwargs):
    if sender == Course and created:
        print("\n\n\nCreated a course object. No Cache to invalidate")
        return

    course_ids = []
    if sender == Course:
        course_ids = [instance.id]
    elif sender == CourseRun:
        course_ids = [instance.course_id]
    elif sender == Program:
        course_ids = instance.courses.all().values_list('id', flat=True)
    elif sender == ProgramPage:
        course_ids = instance.program.courses.all().values_list('id', flat=True)
    elif sender == Product:
        if instance.content_type.model == CourseRun.__name__.lower():
            course_run = instance.run_queryset.first()
            course_ids = [course_run.id]

    if course_ids:
        print("\n\n\nClear cache for Course IDs:", course_ids)
        for course_id in course_ids:
            invalidate_course_cache(course_id)

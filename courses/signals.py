"""
Signals for micromasters course certificates
"""
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from caching.api import invalidate_course_cache
from cms.models import ProgramPage
from courses.models import Course, CourseRun, CourseRunCertificate, Program
from courses.utils import generate_program_certificate
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
@receiver(post_save, sender=ProductVersion)
def handle_course_cache_invalidation(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Handler to invalidate course cache.
    """
    if sender == Course and created:
        return

    course_ids = []
    if sender == Course:
        course_ids = [instance.id]
    elif sender == CourseRun:
        course_ids = [instance.course_id]
    elif sender in (Program, ProgramPage):
        program = instance if sender == Program else instance.program
        course_ids = program.courses.all().values_list("id", flat=True)
    elif sender in (Product, ProductVersion):
        product = instance if sender == Product else instance.product
        if product.content_type.model == CourseRun.__name__.lower():
            course_run = product.run_queryset.first()
            course_ids = [course_run.course.id]

    for course_id in course_ids:
        invalidate_course_cache(course_id)

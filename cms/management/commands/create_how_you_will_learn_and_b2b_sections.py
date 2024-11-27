"""Management command to create How You Will Learn and B2B sections in external course pages"""

from django.core.management.base import BaseCommand

from cms.models import ExternalCoursePage
from cms.wagtail_hooks import create_static_pages_for_external_courses


class Command(BaseCommand):
    """Backfills How You Will Learn and B2B sections to external course pages"""

    help = __doc__

    def handle(self, *args, **options):  # noqa: ARG002
        for page in ExternalCoursePage.objects.all():
            create_static_pages_for_external_courses(None, page)

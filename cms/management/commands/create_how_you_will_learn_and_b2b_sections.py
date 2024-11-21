"""Management command to create How You Will Learn and B2B sections in external course pages"""

from django.core.management.base import BaseCommand

from cms.models import ExternalCoursePage, ForTeamsPage, LearningTechniquesPage
from cms.utils import create_b2b_section, create_how_you_will_learn_section


class Command(BaseCommand):
    """Backfills How You Will Learn and B2B sections to external course pages"""

    help = __doc__

    def handle(self, *args, **options):  # noqa: ARG002
        for page in ExternalCoursePage.objects.all():
            # Check if the sections already exist
            icongrid_page = page.get_child_page_of_type_including_draft(
                LearningTechniquesPage
            )
            if not icongrid_page:
                icongrid_page = create_how_you_will_learn_section()
                page.add_child(instance=icongrid_page)

            # Check if the sections already exist
            b2b_page = page.get_child_page_of_type_including_draft(ForTeamsPage)
            if not b2b_page:
                b2b_page = create_b2b_section()
                page.add_child(instance=b2b_page)

"""Management command to setup courseware index pages"""  # noqa: INP001
from django.core.management.base import BaseCommand

from cms.api import ensure_index_pages


class Command(BaseCommand):
    """Creates courseware index pages and moves the existing courseware pages under the index pages"""  # noqa: E501

    help = __doc__  # noqa: A003

    def handle(self, *args, **options):  # noqa: ARG002
        ensure_index_pages()

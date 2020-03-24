"""Management command to setup courseware index pages"""
from django.core.management.base import BaseCommand

from cms.api import ensure_index_pages


class Command(BaseCommand):
    """Creates courseware index pages and moves the existing courseware pages under the index pages"""

    help = __doc__

    def handle(self, *args, **options):
        ensure_index_pages()

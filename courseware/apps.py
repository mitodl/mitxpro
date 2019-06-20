"""Courseware Django app"""
from django.apps import AppConfig


class CoursewareConfig(AppConfig):
    """AppConfig for courseware"""

    name = "courseware"

    def ready(self):
        """Application is ready"""
        import courseware.signals  # pylint:disable=unused-import, unused-variable

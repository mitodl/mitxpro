"""
Django App
"""
from django.apps import AppConfig


class CoursesConfig(AppConfig):
    """AppConfig for Courses"""

    name = "courses"

    def ready(self):
        """
        Ready handler. Import signals.
        """
        import courses.signals  # pylint: disable=unused-import

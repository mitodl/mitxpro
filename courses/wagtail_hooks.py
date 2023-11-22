"""Wagtail Snippets for courses app"""
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import DeleteView, SnippetViewSet

from courses.models import CourseTopic


class CourseTopicSnippet(SnippetViewSet):
    """Snippet for CourseTopic"""

    model = CourseTopic


register_snippet(CourseTopicSnippet)

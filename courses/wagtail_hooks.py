"""Wagtail Snippets for courses"""
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from wagtail.snippet.views.snippets import DeleteView


class TopicsWagtailDeleteView(DeleteView):
    """Custom view for Topics admin in Wagtail"""

    @property
    def confirmation_message(self):
        child_count = self.instance.subtopics.count()
        if child_count > 0:
            return (
                f"This topic has {child_count} sub-topic(s) that will be deleted as well. Are you sure you want to "
                f"delete? "
            )
        return "Are you sure you want to delete this topic?"


class CourseTopicSnippet(SnippetViewSet):
    """Admin for CourseTopic"""

    model = CourseTopic
    delete_view_class = TopicsWagtailDeleteView


register_snippet(CourseTopicSnippet)

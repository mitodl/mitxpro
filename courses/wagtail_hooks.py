"""Wagtail hooks for courses app"""

from wagtail import hooks

from courses.wagtail_views import CourseTopicViewSet


@hooks.register("register_admin_viewset")
def register_topics_viewset():
    """
    Register `CourseTopicViewSet` in wagtail
    """
    return CourseTopicViewSet("topics")

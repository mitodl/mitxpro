"""Wagtail admin views"""

from wagtail.admin.viewsets.model import ModelViewSet

from courses.models import CourseTopic


class CourseTopicViewSet(ModelViewSet):
    """Wagtail ModelViewSet for CourseTopic"""

    model = CourseTopic
    icon = "snippet"
    search_fields = ["name"]
    form_fields = ["parent", "name"]
    list_display = ["name", "parent"]
    add_to_admin_menu = True

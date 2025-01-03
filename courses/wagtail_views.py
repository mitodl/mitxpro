"""Wagtail admin views"""

from wagtail.admin.viewsets.model import ModelViewSet

from courses.models import CourseLanguage, CourseTopic


class CourseTopicViewSet(ModelViewSet):
    """Wagtail ModelViewSet for CourseTopic"""

    model = CourseTopic
    icon = "snippet"
    search_fields = ["name"]
    form_fields = ["parent", "name"]
    list_display = ["name", "parent"]
    add_to_admin_menu = True


class CourseLanguageViewSet(ModelViewSet):
    """Wagtail ModelViewSet for CourseLanguage"""

    model = CourseLanguage
    icon = "snippet"
    search_fields = ["name"]
    form_fields = ["name", "priority"]
    list_display = ["name", "priority"]
    add_to_admin_menu = True

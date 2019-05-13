"""Course views"""
from rest_framework import viewsets
from django.db.models import Prefetch
from django.views.generic import ListView, DetailView

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from courses.constants import DEFAULT_COURSE_IMG_PATH
from mitxpro.views import get_js_settings_context


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    serializer_class = ProgramSerializer
    queryset = Program.objects.all()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Courses"""

    serializer_class = CourseSerializer
    queryset = Course.objects.all()


class CourseRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for CourseRuns"""

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.all()


class CourseCatalogView(ListView):
    """Course catalog view"""

    template_name = "catalog.html"

    def get_queryset(self):
        sorted_courserun_qset = CourseRun.objects.order_by("start_date")
        programs_qset = (
            Program.objects.live()
            .select_related("programpage")
            .exclude(programpage=None)
            .order_by("id")
            .all()
            .prefetch_related(
                Prefetch("courses__courseruns", queryset=sorted_courserun_qset)
            )
        )
        courses_qset = (
            Course.objects.live()
            .select_related("coursepage")
            .exclude(coursepage=None)
            .order_by("id")
            .all()
            .prefetch_related(Prefetch("courseruns", queryset=sorted_courserun_qset))
        )
        return {"programs": programs_qset, "courses": courses_qset}

    def get_context_data(self, *, object_list=None, **kwargs):
        base_context_data = super().get_context_data(**kwargs)
        object_list = base_context_data.pop("object_list")
        return {
            **base_context_data,
            **get_js_settings_context(self.request),
            "programs": object_list["programs"],
            "courses": object_list["courses"],
            "default_image_path": DEFAULT_COURSE_IMG_PATH,
        }

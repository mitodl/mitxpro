"""Course views"""
from rest_framework import viewsets, status
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.views.generic import ListView, DetailView, CreateView
from django.http import HttpResponse
from django.shortcuts import redirect
from requests.exceptions import HTTPError

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from courses.constants import DEFAULT_COURSE_IMG_PATH
from courseware.api import enroll_in_edx_course_run
from courseware.utils import edx_redirect_url
from mitxpro.views import get_js_settings_context


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    serializer_class = ProgramSerializer
    queryset = Program.objects.select_related("programpage").all()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Courses"""

    serializer_class = CourseSerializer
    queryset = Course.objects.select_related("coursepage").all()


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
            .order_by("id")
            .all()
            .prefetch_related(
                Prefetch("courses__courseruns", queryset=sorted_courserun_qset)
            )
        )
        courses_qset = (
            Course.objects.live()
            .select_related("coursepage")
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


class CourseView(DetailView):
    """Course view"""

    queryset = Course.objects.prefetch_related("courseruns").all()
    template_name = "course_detail.html"

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **get_js_settings_context(self.request),
            "user": self.request.user,
        }


class CourseRunEnrollmentsView(LoginRequiredMixin, CreateView):
    """Course enrollments view"""

    def post(self, request, *args, **kwargs):
        course_run_id = kwargs["course_run_id"]
        try:
            course_run = CourseRun.objects.get(pk=course_run_id)
        except CourseRun.DoesNotExist:
            return HttpResponse(
                content={"error": "Course Run {} does not exist".format(course_run_id)},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            enroll_in_edx_course_run(request.user, course_run)
        except HTTPError as ex:
            return HttpResponse(
                content=ex.response.content, status=ex.response.status_code
            )
        return redirect(edx_redirect_url(course_run.courseware_url_path))

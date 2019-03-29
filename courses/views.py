"""Course views"""
from rest_framework import viewsets, status
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView
from django.http import HttpResponse
from django.shortcuts import redirect
from requests.exceptions import HTTPError

from courses.models import Program, Course, CourseRun
from courses.serializers import ProgramSerializer, CourseSerializer, CourseRunSerializer
from courseware.api import enroll_in_edx_course_run
from courseware.utils import edx_redirect_url
from mitxpro.views import get_js_settings_context


class ProgramViewSet(viewsets.ModelViewSet):
    """API view set for Programs"""

    serializer_class = ProgramSerializer
    queryset = Program.objects.all()


class CourseViewSet(viewsets.ModelViewSet):
    """API view set for Courses"""

    serializer_class = CourseSerializer
    queryset = Course.objects.all()


class CourseRunViewSet(viewsets.ModelViewSet):
    """API view set for CourseRuns"""

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.all()


class CourseCatalogView(ListView):
    """Course catalog view"""

    template_name = "catalog.html"

    def get_queryset(self):
        programs_qset = Program.objects.filter(live=True)
        courses_qset = Course.objects.filter(live=True).order_by("id")
        return {"programs": programs_qset, "courses": courses_qset}

    def get_context_data(self, *, object_list=None, **kwargs):
        base_context_data = super().get_context_data(**kwargs)
        object_list = base_context_data.pop("object_list")
        return {
            **base_context_data,
            **get_js_settings_context(self.request),
            "programs": object_list["programs"],
            "courses": object_list["courses"],
            "default_image_path": "images/mit-dome.png",
        }


class CourseView(DetailView):
    """Course view"""

    queryset = Course.objects.prefetch_related("courserun_set").all()
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

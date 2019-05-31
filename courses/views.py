"""Course views"""
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Prefetch
from django.views.generic import ListView

from courses.models import Program, Course, CourseRun
from courses.api import get_user_enrollments
from courses.serializers import (
    ProgramSerializer,
    CourseSerializer,
    CourseRunSerializer,
    CourseRunEnrollmentSerializer,
    ProgramEnrollmentSerializer,
)
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


class UserEnrollmentsView(APIView):
    """
    View for user program/course enrollments
    """

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """Read-only access"""
        user = request.user
        user_enrollments = get_user_enrollments(user)

        return Response(
            status=status.HTTP_200_OK,
            data={
                "program_enrollments": ProgramEnrollmentSerializer(
                    user_enrollments.programs,
                    many=True,
                    context={
                        "course_run_enrollments": list(user_enrollments.program_runs)
                    },
                ).data,
                "course_run_enrollments": CourseRunEnrollmentSerializer(
                    user_enrollments.non_program_runs, many=True
                ).data,
            },
        )

"""Course views verson 1"""
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Program, Course, CourseRun
from courses.api import get_user_enrollments
from courses.serializers import (
    ProgramSerializer,
    CourseSerializer,
    CourseRunSerializer,
    CourseRunEnrollmentSerializer,
    ProgramEnrollmentSerializer,
)


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    permission_classes = []

    serializer_class = ProgramSerializer
    queryset = Program.objects.filter(live=True).exclude(products=None)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Courses"""

    permission_classes = []

    serializer_class = CourseSerializer
    queryset = Course.objects.filter(live=True)


class CourseRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for CourseRuns"""

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.all()


class UserEnrollmentsView(APIView):
    """
    View for user program/course enrollments
    """

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """Read-only access"""
        user = request.user
        user_enrollments = get_user_enrollments(user)
        program_runs = list(user_enrollments.program_runs)

        return Response(
            status=status.HTTP_200_OK,
            data={
                "program_enrollments": self._serialize_program_enrollments(
                    user_enrollments.programs, program_runs
                ),
                "course_run_enrollments": self._serialize_course_enrollments(
                    user_enrollments.non_program_runs
                ),
                "past_course_run_enrollments": self._serialize_course_enrollments(
                    user_enrollments.past_non_program_runs
                ),
                "past_program_enrollments": self._serialize_program_enrollments(
                    user_enrollments.past_programs, program_runs
                ),
            },
        )

    def _serialize_course_enrollments(self, enrollments):
        """Helper method to serialize course enrollments"""

        return CourseRunEnrollmentSerializer(enrollments, many=True).data

    def _serialize_program_enrollments(self, programs, program_runs):
        """helper method to serialize program enrollments"""

        return ProgramEnrollmentSerializer(
            programs, many=True, context={"course_run_enrollments": list(program_runs)}
        ).data

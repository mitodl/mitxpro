"""Course views verson 1"""
from django.db.models import Prefetch
from mitol.digitalcredentials.mixins import DigitalCredentialsRequestViewSetMixin
from rest_framework import status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.api import get_user_enrollments
from courses.models import (
    Course,
    CourseRun,
    CourseRunCertificate,
    Program,
    ProgramCertificate,
)
from courses.serializers import (
    CourseRunCertificateSerializer,
    CourseRunEnrollmentSerializer,
    CourseRunSerializer,
    CourseSerializer,
    ProgramCertificateSerializer,
    ProgramEnrollmentSerializer,
    ProgramSerializer,
)
from ecommerce.models import Product


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    PRODUCTS_PREFETCH = Prefetch("products", Product.objects.with_ordered_versions())
    COURSE_RUNS_PREFETCH = Prefetch(
        "courseruns", CourseRun.objects.prefetch_related(PRODUCTS_PREFETCH)
    )
    COURSES_PREFETCH = Prefetch(
        "courses",
        Course.objects.select_related("coursepage").prefetch_related(
            COURSE_RUNS_PREFETCH, "topics"
        ),
    )

    permission_classes = []
    serializer_class = ProgramSerializer
    queryset = (
        Program.objects.filter(live=True)
        .exclude(products=None)
        .select_related("programpage")
        .prefetch_related(COURSES_PREFETCH, PRODUCTS_PREFETCH)
    )


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


class CourseRunCertificateViewSet(
    viewsets.ReadOnlyModelViewSet, DigitalCredentialsRequestViewSetMixin
):
    """API for CourseRunCertificate"""

    serializer_class = CourseRunCertificateSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "uuid"

    def get_queryset(self):
        """Get the set of non-revoked certificates for the current user"""
        return CourseRunCertificate.objects.filter(
            user=self.request.user, is_revoked=False
        )

    def get_learner_for_obj(self, certificate: CourseRunCertificate):
        """Get the learner for the CourseRunCertificate"""
        return certificate.user


class ProgramCertificateViewSet(
    viewsets.ReadOnlyModelViewSet, DigitalCredentialsRequestViewSetMixin
):
    """API for ProgramCertificate"""

    serializer_class = ProgramCertificateSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "uuid"

    def get_queryset(self):
        """Get the set of non-revoked certificates for the current user"""
        return ProgramCertificate.objects.filter(
            user=self.request.user, is_revoked=False
        )

    def get_learner_for_obj(self, certificate: ProgramCertificate):
        """Get the learner for the ProgramCertificate"""
        return certificate.user

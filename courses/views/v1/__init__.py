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
    CourseRun,
    CourseRunCertificate,
    CourseTopic,
    ProgramCertificate,
)
from courses.serializers import (
    CourseRunCertificateSerializer,
    CourseRunEnrollmentSerializer,
    CourseRunSerializer,
    CourseSerializer,
    CourseTopicSerializer,
    ProgramCertificateSerializer,
    ProgramEnrollmentSerializer,
    ProgramSerializer,
)
from ecommerce.models import Product


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    permission_classes = []
    serializer_class = ProgramSerializer

    from courses.data_provider import ProgramProvider

    queryset = ProgramProvider().get_data()


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Courses"""

    permission_classes = []
    serializer_class = CourseSerializer

    def get_queryset(self):
        from courses.data_provider import CourseProvider

        queryset = CourseProvider().get_data()

        if self.request.user.is_authenticated:
            enrolled_courseruns_prefetch = Prefetch(
                "courseruns",
                queryset=CourseRun.objects.filter(
                    courserunenrollment__user=self.request.user
                ).only("id", "course_id"),
                to_attr="enrolled_runs",
            )
            queryset = queryset.prefetch_related(enrolled_courseruns_prefetch)

        return queryset.distinct()


class CourseRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for CourseRuns"""

    products_prefetch = Prefetch("products", Product.objects.with_ordered_versions())

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.select_related(
        "course", "course__coursepage", "course__externalcoursepage"
    ).prefetch_related(products_prefetch)


class UserEnrollmentsView(APIView):
    """
    View for user program/course enrollments
    """

    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):  # noqa: ARG002
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
        """Helper method to serialize program enrollments"""

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


class CourseTopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Readonly viewset for parent course topics.
    """

    permission_classes = []
    serializer_class = CourseTopicSerializer

    def get_queryset(self):
        """
        Returns parent topics with course count > 0.
        """
        return CourseTopic.parent_topics_with_courses()

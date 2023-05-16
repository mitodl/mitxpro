"""Course views verson 1"""
from django.db.models import Count, Prefetch, Q
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
    CourseTopic,
    Program,
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
from courses.utils import get_catalog_course_filter
from ecommerce.models import Product
from mitxpro.utils import now_in_utc


class ProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Programs"""

    products_prefetch = Prefetch("products", Product.objects.with_ordered_versions())
    course_runs_prefetch = Prefetch(
        "courseruns", CourseRun.objects.prefetch_related(products_prefetch)
    )
    courses_prefetch = Prefetch(
        "courses",
        Course.objects.select_related("coursepage").prefetch_related(
            course_runs_prefetch, "topics"
        ),
    )

    permission_classes = []
    serializer_class = ProgramSerializer
    queryset = (
        Program.objects.filter(live=True)
        .exclude(products=None)
        .select_related("programpage", "externalprogrampage")
        .prefetch_related(courses_prefetch, products_prefetch)
        .filter(Q(programpage__live=True) | Q(externalprogrampage__live=True))
    )


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for Courses"""

    products_prefetch = Prefetch("products", Product.objects.with_ordered_versions())
    course_runs_prefetch = Prefetch(
        "courseruns", CourseRun.objects.prefetch_related(products_prefetch)
    )

    permission_classes = []
    serializer_class = CourseSerializer

    def get_queryset(self):
        queryset = (
            Course.objects.filter(live=True)
            .select_related("coursepage", "externalcoursepage")
            .prefetch_related("topics", self.course_runs_prefetch)
            .filter(Q(coursepage__live=True) | Q(externalcoursepage__live=True))
        )

        if self.request.user.is_authenticated:
            enrolled_courseruns_prefetch = Prefetch(
                "courseruns",
                queryset=CourseRun.objects.filter(
                    courserunenrollment__user=self.request.user
                ).only("id", "course_id"),
                to_attr="enrolled_runs",
            )
            queryset = queryset.prefetch_related(enrolled_courseruns_prefetch)

        return queryset


class CourseRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API view set for CourseRuns"""

    products_prefetch = Prefetch("products", Product.objects.with_ordered_versions())

    serializer_class = CourseRunSerializer
    queryset = CourseRun.objects.select_related(
        "course", "course__coursepage"
    ).prefetch_related(products_prefetch)


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


class CourseTopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Readonly viewset for parent course topics.
    """

    # CATALOG_VISIBLE_COURSE_FILTER = (
    #     Q(coursepage__course__live=True)
    #     & Q(coursepage__course__courseruns__live=True)
    #     & Q(
    #         Q(
    #             Q(coursepage__course__courseruns__start_date__isnull=False)
    #             & Q(coursepage__course__courseruns__start_date__gt=now_in_utc())
    #         )
    #         | Q(
    #             Q(coursepage__course__courseruns__enrollment_end__isnull=False)
    #             & Q(coursepage__course__courseruns__enrollment_end__gt=now_in_utc())
    #         )
    #     )
    # )

    permission_classes = []
    serializer_class = CourseTopicSerializer

    def get_queryset(self):
        catalog_course_visible_filter = get_catalog_course_filter(
            relative_filter="coursepage__"
        )
        return (
            CourseTopic.objects.filter(parent__isnull=True)
            .annotate(
                internal_course_count=Count(
                    "coursepage", filter=catalog_course_visible_filter, distinct=True
                ),
                external_course_count=Count(
                    "externalcoursepage",
                    filter=Q(externalcoursepage__course__live=True),
                    distinct=True,
                ),
            )
            .prefetch_related(
                Prefetch(
                    "subtopics",
                    CourseTopic.objects.filter(parent__isnull=False).annotate(
                        internal_course_count=Count(
                            "coursepage",
                            filter=catalog_course_visible_filter,
                            distinct=True,
                        ),
                        external_course_count=Count(
                            "externalcoursepage",
                            filter=Q(externalcoursepage__course__live=True),
                            distinct=True,
                        ),
                    ),
                ),
            )
            .order_by("name")
        )

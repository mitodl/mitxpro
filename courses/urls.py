"""Course API URL routes"""

from django.urls import include, path, re_path
from rest_framework import routers

from courses.views import v1
from courses.views.v1 import EmeritusCourseListView

router = routers.SimpleRouter()
router.register(r"programs", v1.ProgramViewSet, basename="programs_api")
router.register(r"courses", v1.CourseViewSet, basename="courses_api")
router.register(r"course_runs", v1.CourseRunViewSet, basename="course_runs_api")
router.register(
    r"parent_course_topics", v1.CourseTopicViewSet, basename="parent_course_topics_api"
)
router.register(
    r"course_run_certificates",
    v1.CourseRunCertificateViewSet,
    basename="course_run_certificates_api",
)
router.register(
    r"program_certificates",
    v1.ProgramCertificateViewSet,
    basename="program_certificates_api",
)

urlpatterns = [
    path("api/v1/", include(router.urls)),
    path("api/", include(router.urls)),
    re_path(
        r"^api/enrollments/", v1.UserEnrollmentsView.as_view(), name="user-enrollments"
    ),
    path(
        "api/emeritus_courses/",
        EmeritusCourseListView.as_view(),
        name="emeritus_courses",
    ),
]

"""Course API URL routes"""
from django.urls import include, re_path
from rest_framework import routers

from courses.views import v1


router = routers.SimpleRouter()
router.register(r"programs", v1.ProgramViewSet, basename="programs_api")
router.register(r"courses", v1.CourseViewSet, basename="courses_api")
router.register(r"course_runs", v1.CourseRunViewSet, basename="course_runs_api")

urlpatterns = [
    re_path(r"^api/v1/", include(router.urls)),
    re_path(r"^api/", include(router.urls)),
    re_path(
        r"^api/enrollments/", v1.UserEnrollmentsView.as_view(), name="user-enrollments"
    ),
]

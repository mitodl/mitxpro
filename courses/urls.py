"""Course API URL routes"""
from django.urls import include, re_path
from rest_framework import routers

from courses import views


router = routers.SimpleRouter()
router.register(r"programs", views.ProgramViewSet, basename="programs_api")
router.register(r"courses", views.CourseViewSet, basename="courses_api")
router.register(r"course_runs", views.CourseRunViewSet, basename="course_runs_api")

urlpatterns = [
    re_path(r"^api/", include(router.urls)),
    re_path(
        r"^api/enrollments/",
        views.UserEnrollmentsView.as_view(),
        name="user-enrollments",
    ),
    re_path(
        r"^courses/(?P<pk>[\d]+)/$", views.CourseView.as_view(), name="course-detail"
    ),
]

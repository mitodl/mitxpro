"""Course API URL routes"""
from django.conf.urls import include, url
from rest_framework import routers

from courses import views


router = routers.SimpleRouter()
router.register(r"programs", views.ProgramViewSet, basename="programs_api")
router.register(r"courses", views.CourseViewSet, basename="courses_api")
router.register(r"course_runs", views.CourseRunViewSet, basename="course_runs_api")

urlpatterns = [url(r"^api/", include(router.urls))]

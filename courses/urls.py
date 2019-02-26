from rest_framework import routers

from courses import views


router = routers.SimpleRouter()
router.register(r"programs", views.ProgramViewSet)
router.register(r"courses", views.CourseViewSet)
router.register(r"course_runs", views.CourseRunViewSet)

urlpatterns = router.urls

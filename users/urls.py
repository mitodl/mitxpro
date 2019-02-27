"""User url routes"""
from django.conf.urls import include
from django.urls import path
from rest_framework import routers

from users.views import UserRetrieveViewSet

router = routers.DefaultRouter()
router.register(r"users", UserRetrieveViewSet, basename="users_api")


urlpatterns = [path("api/", include(router.urls))]

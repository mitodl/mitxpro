"""User url routes"""
from django.conf.urls import include
from django.urls import path
from rest_framework import routers

from users.views import (
    UserRetrieveViewSet,
    CurrentUserRetrieveViewSet,
    CountriesStatesViewSet,
)

router = routers.DefaultRouter()
router.register(r"users", UserRetrieveViewSet, basename="users_api")
router.register(r"countries", CountriesStatesViewSet, basename="countries_api")

urlpatterns = [
    path(
        "api/users/me",
        CurrentUserRetrieveViewSet.as_view({"get": "retrieve"}),
        name="users_api-me",
    ),
    path("api/", include(router.urls)),
]

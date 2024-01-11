"""URL configurations for authentication"""
from django.urls import path
from django.urls.conf import include

from authentication.views import (
    CustomLogoutView,
    LoginEmailView,
    LoginPasswordView,
    RegisterConfirmView,
    RegisterDetailsView,
    RegisterEmailView,
    RegisterExtraDetailsView,
    get_social_auth_types,
    well_known_openid_configuration,
)

urlpatterns = [
    path("api/login/email/", LoginEmailView.as_view(), name="psa-login-email"),
    path("api/login/password/", LoginPasswordView.as_view(), name="psa-login-password"),
    path("api/register/email/", RegisterEmailView.as_view(), name="psa-register-email"),
    path(
        "api/register/confirm/",
        RegisterConfirmView.as_view(),
        name="psa-register-confirm",
    ),
    path(
        "api/register/details/",
        RegisterDetailsView.as_view(),
        name="psa-register-details",
    ),
    path(
        "api/register/extra/",
        RegisterExtraDetailsView.as_view(),
        name="psa-register-extra",
    ),
    path("api/", include("mitol.authentication.urls.djoser_urls")),
    path("api/auths/", get_social_auth_types, name="get-auth-types-api"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    path(
        ".well-known/openid-configuration",
        well_known_openid_configuration,
        name="well-known-openid-configuration",
    ),
]

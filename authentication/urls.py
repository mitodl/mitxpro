"""URL configurations for authentication"""
from django.contrib.auth import views as auth_views
from django.urls import path

from authentication.views import (
    LoginEmailView,
    LoginPasswordView,
    RegisterEmailView,
    RegisterConfirmView,
    RegisterDetailsView,
    RegisterExtraDetailsView,
    get_social_auth_types,
    CustomPasswordResetView,
    CustomPasswordResetConfirmView,
    CustomSetPasswordView,
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
    path(
        "api/password_reset/",
        CustomPasswordResetView.as_view(),
        name="password-reset-api",
    ),
    path(
        "api/password_reset/confirm/",
        CustomPasswordResetConfirmView.as_view(),
        name="password-reset-confirm-api",
    ),
    path("api/set_password/", CustomSetPasswordView.as_view(), name="set-password-api"),
    path("api/auths/", get_social_auth_types, name="get-auth-types-api"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

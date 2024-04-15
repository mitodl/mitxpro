"""Authentication views"""
from urllib.parse import quote, urlencode, urljoin, urlparse

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LogoutView
from django.shortcuts import render, reverse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from social_core.backends.email import EmailAuth
from social_django.models import UserSocialAuth
from social_django.utils import load_backend

from authentication.serializers import (
    LoginEmailSerializer,
    LoginPasswordSerializer,
    RegisterConfirmSerializer,
    RegisterDetailsSerializer,
    RegisterEmailSerializer,
    RegisterExtraDetailsSerializer,
)
from authentication.utils import load_drf_strategy

User = get_user_model()


class SocialAuthAPIView(APIView):
    """API view for social auth endpoints"""

    authentication_classes = []
    permission_classes = []

    def get_serializer_cls(self):  # pragma: no cover
        """Return the serializer cls"""
        raise NotImplementedError("get_serializer_cls must be implemented")  # noqa: EM101

    def post(self, request):
        """Processes a request"""
        if bool(request.session.get("hijack_history")):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer_cls = self.get_serializer_cls()
        strategy = load_drf_strategy(request)
        backend = load_backend(strategy, EmailAuth.name, None)
        serializer = serializer_cls(
            data=request.data,
            context={"request": request, "strategy": strategy, "backend": backend},
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginEmailView(SocialAuthAPIView):
    """Email login view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return LoginEmailSerializer


class LoginPasswordView(SocialAuthAPIView):
    """Email login view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return LoginPasswordSerializer


class RegisterEmailView(SocialAuthAPIView):
    """Email register view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return RegisterEmailSerializer

    def post(self, request):
        """Verify recaptcha response before proceeding"""
        if bool(request.session.get("hijack_history")):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if settings.RECAPTCHA_SITE_KEY:
            r = requests.post(  # noqa: S113
                "https://www.google.com/recaptcha/api/siteverify?secret={key}&response={captcha}".format(
                    key=quote(settings.RECAPTCHA_SECRET_KEY),
                    captcha=quote(request.data["recaptcha"]),
                )
            )
            response = r.json()
            if not response["success"]:
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        return super().post(request)


class RegisterConfirmView(SocialAuthAPIView):
    """Email registration confirmation view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return RegisterConfirmSerializer


class RegisterDetailsView(SocialAuthAPIView):
    """Email registration details view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return RegisterDetailsSerializer


class RegisterExtraDetailsView(SocialAuthAPIView):
    """Email registration extra details view"""

    def get_serializer_cls(self):
        """Return the serializer cls"""
        return RegisterExtraDetailsSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_social_auth_types(request):
    """
    View that returns a serialized list of the logged-in user's UserSocialAuth types
    """
    social_auths = (
        UserSocialAuth.objects.filter(user=request.user).values("provider").distinct()
    )
    return Response(data=social_auths, status=status.HTTP_200_OK)


def confirmation_sent(request, **kwargs):  # noqa: ARG001
    """The confirmation of an email being sent"""
    return render(request, "confirmation_sent.html")


class CustomLogoutView(LogoutView):
    """Custom view to modify base functionality in django.contrib.auth.views.LogoutView"""

    def get_next_page(self):  # noqa: D102
        next_page = super().get_next_page()

        if next_page in (self.next_page, self.request.path):
            return next_page
        else:
            params = {"redirect_url": settings.SITE_BASE_URL}
            next_page += ("&" if urlparse(next_page).query else "?") + urlencode(params)
            return next_page


@api_view(["GET"])
@renderer_classes([JSONRenderer])
@permission_classes([])
def well_known_openid_configuration(request):  # noqa: ARG001
    """View for openid configuration"""
    # See: https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig
    # NOTE: this is intentionally incomplete because we don't fully support OpenID
    #       this was implemented solely for digital credentials
    return Response(
        {
            "issuer": settings.SITE_BASE_URL,
            "authorization_endpoint": urljoin(
                settings.SITE_BASE_URL, reverse("oauth2_provider:authorize")
            ),
            "token_endpoint": urljoin(
                settings.SITE_BASE_URL, reverse("oauth2_provider:token")
            ),
        },
        content_type="application/json",
    )

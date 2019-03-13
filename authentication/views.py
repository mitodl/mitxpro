"""Authentication views"""
from urllib.parse import quote

import requests
from django.conf import settings
from django.core import mail as django_mail
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.shortcuts import render
from social_core.backends.email import EmailAuth
from social_django.models import UserSocialAuth
from social_django.utils import load_backend
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from anymail.message import AnymailMessage
from djoser.views import (
    PasswordResetView as DjoserPasswordResetView,
    PasswordResetConfirmView as DjoserPasswordResetConfirmView,
    SetPasswordView as DjoserSetPasswordView,
)
from djoser.utils import ActionViewMixin
from djoser.email import PasswordResetEmail as DjoserPasswordResetEmail

from authentication.serializers import (
    LoginEmailSerializer,
    LoginPasswordSerializer,
    RegisterEmailSerializer,
    RegisterConfirmSerializer,
    RegisterDetailsSerializer,
)
from authentication.utils import load_drf_strategy
from mail.api import render_email_templates, send_messages

User = get_user_model()


class SocialAuthAPIView(APIView):
    """API view for social auth endpoints"""

    authentication_classes = []
    permission_classes = []

    def get_serializer_cls(self):  # pragma: no cover
        """Return the serializer cls"""
        raise NotImplementedError("get_serializer_cls must be implemented")

    def post(self, request):
        """Processes a request"""
        if request.session.get("is_hijacked_user", False):
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
        """ Verify recaptcha response before proceeding """
        if request.session.get("is_hijacked_user", False):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if settings.RECAPTCHA_SITE_KEY:
            r = requests.post(
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


def confirmation_sent(request, **kwargs):  # pylint: disable=unused-argument
    """The confirmation of an email being sent"""
    return render(request, "confirmation_sent.html")


class CustomPasswordResetEmail(DjoserPasswordResetEmail):
    """Custom class to modify base functionality in Djoser's PasswordResetEmail class"""

    def send(self, to, *args, **kwargs):
        """
        Overrides djoser.email.PasswordResetEmail#send to use our mail API.
        """
        context = self.get_context_data()
        context.update(self.context)
        with django_mail.get_connection(
            settings.NOTIFICATION_EMAIL_BACKEND
        ) as connection:
            subject, text_body, html_body = render_email_templates(
                "password_reset", context
            )
            msg = AnymailMessage(
                subject=subject,
                body=text_body,
                to=to,
                from_email=settings.MAILGUN_FROM_EMAIL,
                connection=connection,
            )
            msg.attach_alternative(html_body, "text/html")
            send_messages([msg])

    def get_context_data(self):
        """Adds base_url to the template context"""
        context = super().get_context_data()
        context["base_url"] = settings.SITE_BASE_URL
        return context


class CustomDjoserAPIView(ActionViewMixin):
    """
    Overrides the post method of a Djoser view and adds one extra piece of logic:

    In version 0.30.0, the fetch function in redux-hammock does not handle responses
    with empty response data. Djoser returns 204's with empty response data, so we are
    coercing that to a 200 with an empty dict as the response data. This can be removed
    when redux-hammock is changed to support 204's.
    """

    def post(self, request, **kwargs):  # pylint: disable=missing-docstring
        response = super().post(request)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            return Response({}, status=status.HTTP_200_OK)
        return response


class CustomPasswordResetView(CustomDjoserAPIView, DjoserPasswordResetView):
    """Custom view to modify base functionality in Djoser's PasswordResetView class"""

    pass


class CustomPasswordResetConfirmView(
    CustomDjoserAPIView, DjoserPasswordResetConfirmView
):
    """Custom view to modify base functionality in Djoser's PasswordResetConfirmView class"""

    pass


class CustomSetPasswordView(CustomDjoserAPIView, DjoserSetPasswordView):
    """Custom view to modify base functionality in Djoser's SetPasswordView class"""

    permission_classes = (IsAuthenticated,)

    def post(self, request, **kwargs):
        """
        Overrides CustomDjoserAPIView.post to update the session after a successful
        password change. Without this explicit refresh, the user's session would be
        invalid and they would be logged out.
        """
        response = super().post(request)
        if response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT):
            update_session_auth_hash(self.request, self.request.user)
        return response

"""Authentication serializers"""

import logging

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from rest_framework import serializers
from social_core.backends.email import EmailAuth
from social_core.exceptions import (
    AuthAssociationError,
    AuthCredentialError,
    AuthException,
    AuthSessionError,
)
from social_core.utils import (
    PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME,
    PARTIAL_TOKEN_PENDING_REQUEST_SESSION_NAME,
    PARTIAL_TOKEN_PENDING_SESSION_NAME,
    partial_pipeline_result,
    sanitize_redirect,
    user_is_active,
    user_is_authenticated,
)
from social_django.views import _do_login as login

from authentication.exceptions import (
    EmailBlockedException,
    InvalidPasswordException,
    RequirePasswordAndPersonalInfoException,
    RequirePasswordException,
    RequireProfileException,
    RequireProviderException,
    RequireRegistrationException,
    UserExportBlockedException,
    UserTryAgainLaterException,
)
from authentication.strategy import ExternalResumeConfirmation
from authentication.utils import SocialAuthState
from users.constants import USER_REGISTRATION_FAILED_MSG

PARTIAL_PIPELINE_TOKEN_KEY = "partial_pipeline_token"  # noqa: S105
# token of the email-verification partial, kept in the session of the browser that registered
EMAIL_VERIFICATION_PARTIAL_TOKEN_KEY = "email_verification_partial_token"  # noqa: S105
# social-core raises AuthCredentialError with this code when an email verification code is invalid
EMAIL_VERIFICATION_REJECTED = "email_verification_rejected"

log = logging.getLogger()

User = get_user_model()


class SocialAuthSerializer(serializers.Serializer):
    """Serializer for social auth"""

    partial_token = serializers.CharField(source="get_partial_token", default=None)
    flow = serializers.ChoiceField(
        choices=(
            (SocialAuthState.FLOW_LOGIN, "Login"),
            (SocialAuthState.FLOW_REGISTER, "Register"),
        )
    )
    provider = serializers.CharField(read_only=True)
    state = serializers.CharField(read_only=True)
    errors = serializers.ListField(read_only=True)
    field_errors = serializers.DictField(read_only=True)
    redirect_url = serializers.CharField(read_only=True, default=None)
    extra_data = serializers.SerializerMethodField()

    def get_extra_data(self, instance):
        """Serialize extra_data"""
        extra_data = dict(instance.extra_data)
        if instance.user is not None:
            extra_data["name"] = instance.user.name
        return extra_data

    def _save_next(self, data):
        """Persists the next url to the session"""
        if "next" in data:
            backend = self.context["backend"]
            # Check and sanitize a user-defined GET/POST next field value
            redirect_uri = data["next"]
            if backend.setting("SANITIZE_REDIRECTS", True):  # noqa: FBT003
                allowed_hosts = backend.setting("ALLOWED_REDIRECT_HOSTS", []) + [  # noqa: RUF005
                    backend.strategy.request_host()
                ]
                redirect_uri = sanitize_redirect(allowed_hosts, redirect_uri)
            backend.strategy.session_set(
                "next", redirect_uri or backend.setting("LOGIN_REDIRECT_URL")
            )

    def _authenticate(self, flow):  # noqa: PLR0911
        """Authenticate the current request"""
        request = self.context["request"]
        strategy = self.context["strategy"]
        backend = self.context["backend"]
        user = request.user

        is_authenticated = user_is_authenticated(user)
        user = user if is_authenticated else None

        kwargs = {"request": request, "flow": flow}

        if not strategy.get_request_data().get("partial_token"):
            # No partial token means the client is starting a new flow: don't let social-core
            # fall back to resuming an abandoned partial bound to this session.
            strategy.session_pop(PARTIAL_PIPELINE_TOKEN_KEY)
        result = partial_pipeline_result(backend, user, **kwargs)
        if isinstance(result.response, ExternalResumeConfirmation):
            confirmation = result.response
            if confirmation.token != strategy.session_get(
                EMAIL_VERIFICATION_PARTIAL_TOKEN_KEY
            ):
                # The verification link was opened in a browser that didn't start this
                # registration; the user has to explicitly confirm before it resumes.
                return SocialAuthState(
                    SocialAuthState.STATE_REGISTER_CONFIRM_REQUIRED,
                    extra_data={
                        "email": confirmation.email,
                        "confirmation_nonce": confirmation.nonce,
                    },
                )
            # same browser that registered, so confirm on the user's behalf
            strategy.confirm_external_resume(confirmation.nonce)
            result = partial_pipeline_result(backend, user, **kwargs)

        partial = result.partial
        if partial is None and result.halt:
            # a partial token was sent but this session isn't allowed to resume it
            raise AuthSessionError(backend, stage="pipeline")
        if partial:
            try:
                user = backend.continue_pipeline(partial)
            except AuthCredentialError as exc:
                if exc.code != EMAIL_VERIFICATION_REJECTED:
                    raise
                authentication_flow = partial.data.get("kwargs").get("flow")
                if (
                    authentication_flow
                    and authentication_flow == SocialAuthState.FLOW_REGISTER
                ):
                    email = partial.data.get("kwargs").get("details").get("email")
                    user_exists = User.objects.filter(email__iexact=email).exists()

                    if user_exists:
                        return SocialAuthState(SocialAuthState.STATE_EXISTING_ACCOUNT)
                    return SocialAuthState(SocialAuthState.STATE_INVALID_LINK)
                return SocialAuthState(SocialAuthState.STATE_INVALID_EMAIL)
            except AuthAssociationError:
                return SocialAuthState(SocialAuthState.STATE_EXISTING_ACCOUNT)
            # clean partial data after usage
            strategy.clean_partial_pipeline(partial.token)
        else:
            user = backend.complete(user=user, **kwargs)

        # pop redirect value before the session is trashed on login(), but after
        # the pipeline so that the pipeline can change the redirect if needed
        redirect_url = backend.strategy.session_get("next", None)

        # check if the output value is something else than a user and just
        # return it to the client
        user_model = strategy.storage.user.user_model()
        if user and not isinstance(user, user_model):
            # this is where a redirect from the pipeline would get returned
            return user

        if is_authenticated:
            return SocialAuthState(
                SocialAuthState.STATE_SUCCESS, redirect_url=redirect_url
            )
        elif user:
            if user_is_active(user):
                social_user = user.social_user

                login(backend, user, social_user)
                # store last login backend name in session
                strategy.session_set(
                    "social_auth_last_login_backend", social_user.provider
                )

                return SocialAuthState(
                    SocialAuthState.STATE_SUCCESS, redirect_url=redirect_url
                )
            else:
                return SocialAuthState(SocialAuthState.STATE_INACTIVE)
        else:  # pragma: no cover
            # this follows similar code in PSA itself, but wasn't reachable through normal testing
            log.error("Unexpected authentication result")
            return SocialAuthState(
                SocialAuthState.STATE_ERROR, errors=["Unexpected authentication result"]
            )

    def save(self, **kwargs):  # noqa: C901
        """'Save' the auth request"""
        try:
            result = super().save(**kwargs)
        except RequireProviderException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_LOGIN_PROVIDER,
                provider=exc.social_auth.provider,
                user=exc.social_auth.user,
            )
        except UserExportBlockedException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_USER_BLOCKED,
                errors=[f"Error code: CS_{exc.reason_code}"],
            )
        except RequireProfileException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_REGISTER_EXTRA_DETAILS, partial=exc.partial
            )
        except RequirePasswordAndPersonalInfoException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_REGISTER_DETAILS,
                partial=exc.partial,
                errors=exc.errors or [],
                field_errors=exc.field_errors or {},
            )
        except UserTryAgainLaterException:
            result = SocialAuthState(
                SocialAuthState.STATE_ERROR_TEMPORARY,
                errors=[USER_REGISTRATION_FAILED_MSG],
            )
        except AuthException as exc:
            if (
                isinstance(exc, AuthCredentialError)
                and exc.code == EMAIL_VERIFICATION_REJECTED
            ):
                result = SocialAuthState(SocialAuthState.STATE_INVALID_EMAIL)
            else:
                log.exception("Received unexpected AuthException")
                result = SocialAuthState(SocialAuthState.STATE_ERROR, errors=[str(exc)])

        if isinstance(result, SocialAuthState):
            if result.partial is not None:
                strategy = self.context["strategy"]
                strategy.storage.partial.store(result.partial)
                # social-core only resumes a partial owned by this browser's session; the
                # partial_token sent back by the client is not accepted on its own.
                strategy.session_set(PARTIAL_PIPELINE_TOKEN_KEY, result.partial.token)
            if result.state == SocialAuthState.STATE_REGISTER_CONFIRM_SENT:
                # If the user has just signed up and a verification link has been emailed, we need
                # to remove the partial token from the session. The partial token refers to a Partial
                # object, and we only want to continue the pipeline with that object if the user has
                # clicked the email verification link and the Partial has been matched from
                # the verification URL (that URL also contains the verification code, which we need
                # to continue the pipeline). Remember the token separately so that opening the
                # link in this same browser can resume without an extra confirmation step.
                session = self.context["backend"].strategy.session
                session[EMAIL_VERIFICATION_PARTIAL_TOKEN_KEY] = session.pop(
                    PARTIAL_PIPELINE_TOKEN_KEY
                )
        else:
            # if we got here, we saw an unexpected result
            log.error("Received unexpected result: %s", result)
            result = SocialAuthState(SocialAuthState.STATE_ERROR)

        # return the passed flow back to the caller
        # this way they know if they're on a particular page because of an attempted registration or login
        result.flow = self.validated_data["flow"]

        if result.provider is None:
            result.provider = EmailAuth.name

        # update self.instance so we serializer the reight object
        self.instance = result

        return result


class LoginEmailSerializer(SocialAuthSerializer):
    """Serializer for email login"""

    partial_token = serializers.CharField(
        source="get_partial_token", read_only=True, default=None
    )
    email = serializers.EmailField(write_only=True)
    next = serializers.CharField(write_only=True, required=False)

    def create(self, validated_data):
        """Try to 'save' the request"""
        self._save_next(validated_data)

        try:
            result = super()._authenticate(SocialAuthState.FLOW_LOGIN)
        except RequireRegistrationException:
            result = SocialAuthState(
                SocialAuthState.STATE_REGISTER_REQUIRED,
                field_errors={"email": "Couldn't find your account"},
            )
        except RequirePasswordException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_LOGIN_PASSWORD,
                partial=exc.partial,
                user=User.objects.filter(
                    social_auth__uid=validated_data.get("email"),
                    social_auth__provider=EmailAuth.name,
                ).first(),
            )
        return result


class LoginPasswordSerializer(SocialAuthSerializer):
    """Serializer for email login with password"""

    password = serializers.CharField(min_length=8, write_only=True)

    def create(self, validated_data):  # noqa: ARG002
        """Try to 'save' the request"""
        try:
            result = super()._authenticate(SocialAuthState.FLOW_LOGIN)
        except InvalidPasswordException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_ERROR,
                partial=exc.partial,
                field_errors={"password": str(exc)},
            )
        return result


class RegisterEmailSerializer(SocialAuthSerializer):
    """Serializer for email register"""

    email = serializers.EmailField(write_only=True, required=False)
    next = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        token = (attrs.get("partial", {}) or {}).get("token", None)
        email = attrs.get("email", None)
        if not email and not token:
            raise serializers.ValidationError("One of 'partial' or 'email' is required")  # noqa: EM101

        if email and token:
            raise serializers.ValidationError("Pass only one of 'partial' or 'email'")  # noqa: EM101

        return attrs

    def create(self, validated_data):
        """Try to 'save' the request"""
        self._save_next(validated_data)

        if validated_data.get("email"):
            # Starting a new registration abandons any verification link this browser was
            # asked to confirm (e.g. the user chose "not my email" on the confirm page).
            strategy = self.context["strategy"]
            for key in (
                PARTIAL_TOKEN_PENDING_SESSION_NAME,
                PARTIAL_TOKEN_PENDING_REQUEST_SESSION_NAME,
                PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME,
            ):
                strategy.session_pop(key)

        try:
            result = super()._authenticate(SocialAuthState.FLOW_REGISTER)
            if isinstance(result, HttpResponseRedirect):
                # a redirect here means confirmation email sent
                result = SocialAuthState(SocialAuthState.STATE_REGISTER_CONFIRM_SENT)
        except RequirePasswordException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_LOGIN_PASSWORD,
                partial=exc.partial,
                errors=[str(exc)],
            )
        except EmailBlockedException as exc:
            result = SocialAuthState(
                SocialAuthState.STATE_REGISTER_EMAIL,
                partial=exc.partial,
                errors=[str(exc)],
            )
        return result


class RegisterConfirmSerializer(SocialAuthSerializer):
    """Serializer for email confirmation"""

    partial_token = serializers.CharField(source="get_partial_token")
    verification_code = serializers.CharField(write_only=True)

    def create(self, validated_data):  # noqa: ARG002
        """Try to 'save' the request"""
        return super()._authenticate(SocialAuthState.FLOW_REGISTER)


class RegisterDetailsSerializer(SocialAuthSerializer):
    """Serializer for registration details"""

    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(write_only=True)

    def create(self, validated_data):  # noqa: ARG002
        """Try to 'save' the request"""
        return super()._authenticate(SocialAuthState.FLOW_REGISTER)


class RegisterExtraDetailsSerializer(SocialAuthSerializer):
    """Serializer for registration details"""

    gender = serializers.CharField(write_only=True)
    birth_year = serializers.CharField(write_only=True)
    company = serializers.CharField(write_only=True)
    job_title = serializers.CharField(write_only=True)
    industry = serializers.CharField(write_only=True, allow_blank=True, required=False)
    job_function = serializers.CharField(
        write_only=True, allow_blank=True, required=False
    )
    years_experience = serializers.CharField(
        write_only=True, allow_blank=True, required=False
    )
    company_size = serializers.CharField(
        write_only=True, allow_blank=True, required=False
    )
    leadership_level = serializers.CharField(
        write_only=True, allow_blank=True, required=False
    )
    highest_education = serializers.CharField(
        write_only=True, allow_blank=True, required=False
    )

    def create(self, validated_data):  # noqa: ARG002
        """Try to 'save' the request"""
        return super()._authenticate(SocialAuthState.FLOW_REGISTER)

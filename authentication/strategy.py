"""Custom strategy"""

from dataclasses import dataclass

from social_core.utils import PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME
from social_django.strategy import (
    PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER,
    DjangoStrategy,
)

PARTIAL_PIPELINE_CONFIRMATION_PARAMETER = "partial_pipeline_confirm"


@dataclass(frozen=True)
class ExternalResumeConfirmation:
    """
    Returned in place of social-django's HTML confirmation page when a partial pipeline
    (email verification) is resumed from a link, so the API can ask the client to confirm.
    """

    token: str
    nonce: str
    email: str | None


class DjangoRestFrameworkStrategy(DjangoStrategy):
    """Strategy specific to handling DRF requests"""

    def __init__(self, storage, drf_request=None, tpl=None):
        self.drf_request = drf_request
        self.extra_request_data = {}
        # pass the original django request to DjangoStrategy
        request = drf_request._request  # noqa: SLF001
        super().__init__(storage, request=request, tpl=tpl)

    def get_request_data(self, merge=True):  # noqa: ARG002, FBT002
        """
        Returns the current request's data. social-core 6 reads the framework request through
        this hook; request_data() layers replayed partial-pipeline data on top of it.
        """
        if not self.drf_request:
            return {}

        # DRF stores json payload data here, not in request.POST or request.GET like PSA expects
        if not self.extra_request_data:
            return self.drf_request.data
        return {**self.drf_request.data, **self.extra_request_data}

    def partial_pipeline_external_resume_confirmation(
        self,
        backend,  # noqa: ARG002
        partial,
        request_data,  # noqa: ARG002
    ):
        """Record a confirmation nonce in the session and return it instead of rendering HTML"""
        nonce = self.random_string(32)
        self.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, nonce)
        return ExternalResumeConfirmation(
            token=partial.token,
            nonce=nonce,
            email=(partial.kwargs.get("details") or {}).get("email"),
        )

    def confirm_external_resume(self, nonce):
        """Confirm a pending external resume on behalf of the client"""
        self.extra_request_data = {
            PARTIAL_PIPELINE_CONFIRMATION_PARAMETER: "1",
            PARTIAL_PIPELINE_CONFIRMATION_NONCE_PARAMETER: nonce,
        }

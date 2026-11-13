"""Custom strategy"""

from collections.abc import Mapping
from dataclasses import dataclass

from django.utils.datastructures import MultiValueDict
from social_core.utils import (
    PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME,
    PARTIAL_TOKEN_PENDING_SESSION_NAME,
)
from social_django.strategy import DjangoStrategy

# request fields that must never be written to stored partials or the session
SENSITIVE_REQUEST_FIELDS = frozenset({"password"})


@dataclass(frozen=True)
class ExternalResumeConfirmation:
    """
    Returned in place of social-django's HTML confirmation page when a partial pipeline
    (email verification) is resumed from a link, so the API can ask the client to confirm.
    """

    nonce: str
    email: str | None


class DjangoRestFrameworkStrategy(DjangoStrategy):
    """Strategy specific to handling DRF requests"""

    def __init__(self, storage, drf_request=None, tpl=None):
        self.drf_request = drf_request
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

        # DRF stores json payload data here, not in request.POST or request.GET like PSA expects.
        # Form-encoded data arrives as a QueryDict; dict-unpacking one copies its internal lists,
        # so normalize to plain values before anything (here or in social-core) merges it.
        data = self.drf_request.data
        if isinstance(data, MultiValueDict):
            return data.dict()
        # a JSON body that isn't an object (123, "abc", [1], null) has no fields; the serializer
        # rejects it with a 400
        return dict(data) if isinstance(data, Mapping) else {}

    def to_session_value(self, val):
        """
        Never persist passwords: social-core 6 snapshots request data into every stored partial
        (social_auth_partial) and into the session. Steps still read the live request.
        """
        if isinstance(val, MultiValueDict):
            val = val.dict()
        if isinstance(val, dict) and not SENSITIVE_REQUEST_FIELDS.isdisjoint(val):
            val = {k: v for k, v in val.items() if k not in SENSITIVE_REQUEST_FIELDS}
        return super().to_session_value(val)

    def partial_pipeline_external_resume_confirmation(
        self,
        backend,  # noqa: ARG002
        partial,
        request_data,  # noqa: ARG002
    ):
        """Record a confirmation nonce in the session and return it instead of rendering HTML"""
        # Reuse the nonce if this link is already pending here, so opening it in a second tab
        # doesn't invalidate the Continue button in the first one.
        nonce = None
        if self.session_get(PARTIAL_TOKEN_PENDING_SESSION_NAME) == partial.token:
            nonce = self.session_get(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME)
        nonce = nonce or self.random_string(32)
        self.session_set(PARTIAL_TOKEN_PENDING_CONFIRMATION_SESSION_NAME, nonce)
        return ExternalResumeConfirmation(
            nonce=nonce,
            email=(partial.kwargs.get("details") or {}).get("email"),
        )
